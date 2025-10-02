import io
import numpy as np
import librosa
import soundfile as sf
import onnxruntime as rt
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import audio_transcriber


def wav_bytes_to_raw_int16(wav_bytes: bytes) -> bytes:
    """
    Конвертирует WAV-байты в сырые int16 PCM байты (моно, 16 кГц).
    """
    with io.BytesIO(wav_bytes) as f:
        data, sr = sf.read(f, dtype="float32")
    if len(data.shape) > 1:
        data = librosa.to_mono(data.T)
    if sr != 16000:
        data = librosa.resample(
            data,
            orig_sr=sr,
            target_sr=16000,
            res_type="soxr_hq"
        )
    int16_audio = (data * 32767).astype(np.int16)
    return int16_audio.tobytes()


class LongAudioTranscribe:
    def __init__(
            self,
            transcribator: audio_transcriber.AudioTranscriber,
            model_path: str = "./", 
            frame_rate: int = 16000, 
            chunk_size: int = 512,
            voice_treshold: float = 0.24
    ) -> None:
        """
        """
        self.trr = transcribator
        opts = rt.SessionOptions()
        opts.intra_op_num_threads = 1
        self.model_session = rt.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"], 
            sess_options=opts
        )
        self.frame_rate = frame_rate
        self.chunk_size = chunk_size
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.confidence_level = voice_treshold
    
    def reset_state(self):
        self.state = np.zeros((2, 1, 128), dtype=np.float32)

    def predict_chunk(self, audio_chunk: np.ndarray) -> float:
        inputs_dict = {
            "input": np.expand_dims(audio_chunk, axis=0),
            "state": self.state,
            "sr": np.array([self.frame_rate], dtype=np.int64)
        }
        try:
            outputs = self.model_session.run(["output", "stateN"], inputs_dict)
            self.state = outputs[1]
            return float(outputs[0][0][0]) > self.confidence_level
        except Exception as e:
            print(f"Ошибка при выполнении модели ONNX: {e}")

    def transcribe_long_audio(self, audio_bytes: bytes) -> list:
        self.reset_state()
        audio_array = (np.frombuffer(audio_bytes, dtype=np.int16) / 32767.0).astype(np.float32)
        in_speech = False
        audio_buffer = deque(maxlen=40)
        phrase = []
        results = []
        current_time = 0.0
        phrase_start_time = 0.0
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures_with_times = []
            for i in range(0, len(audio_array), self.chunk_size):
                chunk = audio_array[i:i + self.chunk_size]
                if len(chunk) == 0:
                    break
                chunk_duration = len(chunk) / self.frame_rate
                is_speech = self.predict_chunk(chunk)
                if not is_speech and not in_speech:
                    audio_buffer.append(chunk)
                    current_time += chunk_duration
                    continue
                if is_speech:
                    if not in_speech:
                        in_speech = True
                        self.confidence_level = 0.01
                        phrase_start_time = current_time - (len(audio_buffer) * self.chunk_size / self.frame_rate)
                        phrase = list(audio_buffer)
                    phrase.append(chunk)
                elif not is_speech and in_speech:
                    in_speech = False
                    self.confidence_level = 0.24
                    phrase.append(chunk)
                    if phrase:
                        concatenated_phrase = np.concatenate(phrase)
                        phrase_end_time = current_time + chunk_duration
                        future = executor.submit(self.trr.transcribe, concatenated_phrase)
                        futures_with_times.append((future, phrase_start_time, phrase_end_time))
                    audio_buffer.clear()
                    phrase = []
                current_time += chunk_duration
            if in_speech and phrase:
                concatenated_phrase = np.concatenate(phrase)
                phrase_end_time = current_time
                future = executor.submit(self.trr.transcribe, concatenated_phrase)
                futures_with_times.append((future, phrase_start_time, phrase_end_time))
            for future, start_time, end_time in futures_with_times:
                res = future.result().strip()
                if res:
                    results.append({
                        "start_time": round(start_time, 3),
                        "end_time": round(end_time, 3),
                        "text": res
                    })
        return results