from io import BytesIO
import shutil
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from langchain_openai import ChatOpenAI

import audio_transcriber
from long_trr import LongAudioTranscribe, wav_bytes_to_raw_int16
from vlm_pipe import CVPipe


trr = audio_transcriber.AudioTranscriber(
    "/home/yarolit/Models/sber_audio/v2_ctc.onnx"
)
long_trr = LongAudioTranscribe(
    trr, 
    model_path="/home/yarolit/Models/sber_audio/silero_vad.onnx"
)
params = {
    "model": "Qwen2.5-VL-32B",
    "openai_api_base": "http://localhost:8888/v1",
    "openai_api_key": "sk-not-required",
    "temperature": 0,
    "max_tokens": 8192,
    "timeout": 60,
    "max_retries": 2
}
vllm = ChatOpenAI(**params)
cv_pipe = CVPipe(vllm)
app = FastAPI()


MAX_FILE_SIZE = 10 * 1024 * 1024


@app.get("/")
async def root():
    return "Server is ON"

@app.post("/process-audio")
async def long_transcribe(request: Request):
    try:
        audio_bytes = await request.body()
        if audio_bytes.startswith(b"RIFF"):
            audio_bytes = wav_bytes_to_raw_int16(audio_bytes)
        text = long_trr.transcribe_long_audio(audio_bytes)
        return {"message": text}
    except Exception as e:
        print(f"Ошибка транскрибации: {e}")
        return {"message": f"Ошибка транскрибации: {e}"}

@app.post("/process-image")
async def extract_text(file: UploadFile = File(...)):
    """
    """
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Файл слишком большой (макс. 10 МБ)")
    try:
        file_buffer = BytesIO()
        shutil.copyfileobj(file.file, file_buffer)
        file_buffer.seek(0)
        result = await cv_pipe(file_buffer)
        return JSONResponse(content={"result": result})
    except HTTPException:
        raise
    except Exception as e:
        print(f"Неизвестная системная ошибка: {e}")
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка сервера."
        )
    finally:
        await file.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004, log_level="info")