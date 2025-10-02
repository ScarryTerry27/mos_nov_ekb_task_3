import os
import io
import cv2
import json
import numpy as np
import asyncio
import requests
import subprocess
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from PIL import Image
import logging
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import Image as ReportLabImage

from PIL import Image as PILImage
import io

from typing import List, Tuple

# from services.db import schema


# def analyze_video(video_bytes: bytes) -> Tuple[schema.CheckBase, List[schema.IncidentBase]]:
#     """Mock video analysis that returns check and incident metadata.
#
#     This function pretends to forward the provided video to an external
#     detection service. Until the real integration is implemented we return
#     deterministic metadata that can be stored in the database.
#     """
#
#     check_data = schema.CheckBase(
#         info="Automatically generated inspection from video",
#         location="Video stream location",
#         status_check=schema.CheckStatusEnum.INCIDENT,
#     )
#
#     incidents_data = [
#         schema.IncidentBase(
#             photo="video_frame_reference",
#             incident_status=True,
#             incident_info="Potential safety violation detected in the video",
#             prescription_type=schema.PrescriptionTypeEnum.TYPE_1,
#         )
#     ]
#
#     return check_data, incidents_data

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class VideoPipe:
    def __init__(
            self,
            llm: ChatOpenAI,
            trr_serv_url: str = "http://0.0.0.0:8008/transcribe_long"
            # Тут надо будет переделать на адрес моего микросервиса транскрибации
    ) -> None:
        """
        """
        self.trr_serv_url = trr_serv_url
        self.llm = llm

    async def __call__(self, video_input: Optional[bytes | str]):
        """
        """
        try:
            audio_bytes = self.extract_audio_bytes(video_input, normalize=True)
        except Exception as err:
            print('-------------------1')
            print(err)
            return
        try:
            phrases = self.send_transcribe(audio_bytes)
            if not isinstance(phrases, List) or not phrases:
                print('-------------------2')
                return
        except:
            return
        try:
            res = await self.llm_analyse(phrases)
            time_ranges = []
            descriptions = []
            for issue in res.issues:
                idx = issue.idx
                if idx < len(phrases):
                    phrase = phrases[idx]
                    time_ranges.append((phrase["start_time"], phrase["end_time"]))
                    descriptions.append(issue.description)
        except Exception as e:
            print('-------------------3')
            return
        try:
            # в начале __call__ перед extract_video_segments
            os.makedirs("segments", exist_ok=True)
            frames_path = self.extract_video_segments(video_input, time_ranges, output_dir="segments")
        except Exception as e:
            print(e)
            print('-------------------4')
            return
        try:
            issue_images = []
            for frames in frames_path:
                best_frames = self.extract_sharp_frames(frames)
                if best_frames:
                    best_frame = best_frames[0][2]
                    issue_images.append(best_frame)
                else:
                    issue_images.append(None)
        except Exception:
            return
        self.cleanup_temp_files(frames_path)  # удаляем временные файлы
        issues_list = [
            {"img": img_data, "description": desc}
            for img_data, desc in zip(issue_images, descriptions)
            if img_data is not None
        ]
        return phrases, issues_list

    async def llm_analyse(self, phrases: List[Dict], timeout: float = 60.0):
        """
        Анализирует расшифровку с помощью LLM (DeepSeek), возвращает структурированный результат.
        """

        class Issue(BaseModel):
            idx: int = Field(
                description="Индекс фразы из расшифровки",
                examples=[1, 7]
            )
            description: str = Field(
                description="Описание выявленного нарушения",
                examples=["Отсутствие крепежных болтов поперечных балок"]
            )

        class AnswerStruct(BaseModel):
            issues: List[Issue] = Field(
                description="Список выявленных нарушений с описанием"
            )

        text = "\n".join(f"{idx} --> {phrase}" for idx, phrase in enumerate(phrases))
        sys_msg = SystemMessage(content="""Ты — многофункциональный помощник \
инспектора строительного контроля.
Входные данные: расшифровка видеозаписи процесса обследования строительного объекта \
(транскрибированный текст) в формате: <индекс> --> <текст фразы>

ЗАДАЧА:
Проанализируй расшифровку и найди фразы, в которых пользователь \
указывает на наличие нарушений (дефектов, отклонений, несоответствий).
Для каждой такой фразы запомни её индекс и сформулируй краткое описание нарушения \
в строгом деловом стиле, принятом в строительной документации.

ФОРМАТ ОТВЕТА:
Верни ТОЛЬКО валидный JSON-объект в следующем формате:
{
"issues": [
    {"idx": <номер фразы>, "description": "<описание нарушения>"},
    ...
]
}
Если нарушений не найдено, верни: {"issues": []}

НЕ ДОБАВЛЯЙ ПОЯСНЕНИЙ, КОММЕНТАРИЕВ, МАРКДАУНА ИЛИ ДОПОЛНИТЕЛЬНОГО ТЕКСТА. ТОЛЬКО ЧИСТЫЙ JSON.""")
        usr_msg = HumanMessage(content=text)
        try:
            async with asyncio.timeout(timeout):
                response = await self.llm.ainvoke([sys_msg, usr_msg])
            cleaned = response.content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
                if cleaned.endswith("```"):
                    cleaned = cleaned.rsplit("\n", 1)[0]
            raw_data = json.loads(cleaned)
            answer = AnswerStruct(**raw_data)
            if not answer.issues:
                logger.warning("Получен пустой список нарушений")
            else:
                logger.info(f"Получено нарушений: {len(answer.issues)}")
            return answer
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Не удалось распарсить или валидировать ответ LLM: {e}\nОтвет: {cleaned}")
            print(f"Не удалось распарсить или валидировать ответ LLM: {e}\nОтвет: {cleaned}")
            return None
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при вызове LLM: {timeout} секунд")
            print(f"Таймаут при вызове LLM: {timeout} секунд")
            return None
        except Exception as e:
            print(f"Ошибка при вызове LLM: {e}")
            logger.error(f"Ошибка при вызове LLM: {e}")
            return None

    def send_transcribe(self, audio_bytes: bytes) -> List:
        """
        """
        response = None
        message = []
        try:
            response = requests.post(
                self.trr_serv_url,
                data=audio_bytes,
                headers={"Content-Type": "application/octet-stream"},
                timeout=300
            )
            print(response.status_code)
            response.raise_for_status()
            json_data = response.json()
            if "message" not in json_data:
                logger.error("Ключ 'message' отсутствует в ответе")
                logger.error("Тело ответа: %s", json_data)
            else:
                message = json_data["message"]
                if not isinstance(message, list) or len(message) == 0:
                    logger.error("'message' является пустым списком")
                    logger.error("Тело ответа: %s", json_data)
                else:
                    if all(isinstance(item, dict) for item in message):
                        logger.info("Успешно: 'message' содержит список словарей")
                        logger.info("Результат: %s", message)
                        return message
                    else:
                        logger.error("Не все элементы 'message' являются словарями")
                        logger.error("Тело ответа: %s", json_data)
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP ошибка: %s", e)
            if response is not None:
                logger.error("Статус: %s", response.status_code)
                logger.error("Тело ответа: %s", response.text)
        except requests.exceptions.ConnectionError as err:
            print(err)
            print(self.trr_serv_url)
            logger.error("Ошибка подключения: не удалось подключиться к серверу")
        except requests.exceptions.Timeout:
            logger.error("Таймаут: сервер не ответил за 300 секунд")
        except requests.exceptions.RequestException as e:
            logger.error("Ошибка запроса: %s", e)
        except ValueError:
            if response is not None:
                logger.error("Ошибка: сервер вернул некорректный JSON")
                logger.error("Тело ответа: %s", response.text)
        return message

    @staticmethod
    def extract_audio_bytes(video_input: Optional[bytes | str], normalize=True) -> bytes:
        """
        Извлекает аудио из видео и возвращает его в виде сырых int16 PCM байтов.
        Гарантирует, что длина байтов кратна 2.
        """
        is_bytes = isinstance(video_input, bytes)
        command = [
            "ffmpeg",
            "-i", "pipe:0" if is_bytes else video_input,
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ac", "1",
            "-ar", "16000",
        ]
        if normalize:
            command += ["-af", "loudnorm"]
        command += [
            "-y",
            "-"
        ]
        result = subprocess.run(
            command,
            input=video_input if is_bytes else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {result.stderr.decode()}")
        audio_bytes = result.stdout
        if len(audio_bytes) % 2 != 0:
            audio_bytes = audio_bytes[:-1]
        return audio_bytes

    @staticmethod
    def extract_frames_at_timestamps(
            video_input: Optional[bytes | str],
            timestamps: List[float],
            output_dir=None
    ) -> List[Tuple[float, int, bytes]]:
        """
        Извлекает кадры из видео по указанным временным меткам.
        """
        is_bytes = isinstance(video_input, bytes)
        frames = []
        for i, ts in enumerate(timestamps):
            command = [
                "ffmpeg",
                "-ss", str(ts),
                "-i", "pipe:0" if is_bytes else video_input,
                "-vframes", "1",
                "-f", "image2",
                "-v", "error",
                "-"
            ]
            result = subprocess.run(
                command,
                input=video_input if is_bytes else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg error at timestamp {ts}: {result.stderr.decode()}")
            image_bytes = result.stdout
            image = Image.open(io.BytesIO(image_bytes))
            frame = np.array(image)
            if output_dir:
                path = f"{output_dir}/frame_{i:04d}_at_{ts:.2f}s.jpg"
                image.save(path)
                frames.append(path)
            else:
                frames.append(frame)
        return frames

    @staticmethod
    def extract_video_segments(
            video_input: Optional[bytes | str],
            timestamps: List[Tuple[float, float]],
            output_dir: str
    ) -> List[str]:
        """
        Извлекает фрагменты видео по временным меткам и сохраняет их на диск.
        """
        is_bytes = isinstance(video_input, bytes)
        segments = []
        for i, (start, end) in enumerate(timestamps):
            duration = end - start
            output_path = os.path.join(output_dir, f"segment_{i:04d}_{start:.2f}-{end:.2f}.mp4")
            command = [
                "ffmpeg",
                "-ss", str(start),
                "-t", str(duration),
                "-i", "pipe:0" if is_bytes else video_input,
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                "-y",
                output_path
            ]
            result = subprocess.run(
                command,
                input=video_input if is_bytes else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg error for segment {i} ({start}s - {end}s): {result.stderr.decode()}")
            segments.append(output_path)
        return segments

    @staticmethod
    def extract_sharp_frames(video_path: str, top_n=1, method="laplacian"):
        """
        """
        cap = cv2.VideoCapture(video_path)
        scores = []
        frame_idx = 0
        score = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if method == "laplacian":
                score = cv2.Laplacian(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
            elif method == "sobel":
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
                grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
                score = cv2.magnitude(grad_x, grad_y).var()
            elif method == "tenengrad":
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
                grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
                grad = grad_x ** 2 + grad_y ** 2
                score = grad.mean()
            scores.append((score, frame_idx, frame.copy()))
            frame_idx += 1
        cap.release()
        scores.sort(key=lambda x: x[0], reverse=True)
        top_frames = scores[:top_n]
        return top_frames

    @staticmethod
    def cleanup_temp_files(file_paths: List[str]) -> None:
        """
        Удаляет список временных файлов, игнорируя ошибки (но логируя их).
        """
        for path in file_paths:
            if path is None:
                continue
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.debug(f"Удалён временный файл: {path}")
                else:
                    logger.debug(f"Файл не существует (пропускаем): {path}")
            except OSError as e:
                logger.warning(f"Не удалось удалить временный файл {path}: {e}")
            except Exception as e:
                logger.error(f"Неожиданная ошибка при удалении {path}: {e}")


class ReportGenerator:
    def __init__(self, font_name='DejaVuSans'):
        self.font_name = font_name
        try:
            pdfmetrics.registerFont(TTFont(self.font_name, f'{self.font_name}.ttf'))
        except Exception:
            self.font_name = 'Helvetica'

    def _numpy_to_image_buffer(self, np_array):
        """Конвертирует numpy array (BGR) в буфер BytesIO с изображением (RGB)."""
        if np_array.ndim == 3 and np_array.shape[2] == 3:
            img = PILImage.fromarray(np_array[:, :, ::-1])  # BGR -> RGB
        else:
            img = PILImage.fromarray(np_array)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

    def create_report(self, filename: str, address: str, customer: str, contractor: str, check_date: str,
                      violations: list):
        page_width, _ = landscape(A4)
        doc = SimpleDocTemplate(filename, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=1,
            spaceAfter=30,
            fontName=self.font_name,
        )
        centered_style = ParagraphStyle(
            'Centered',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=12,
            alignment=1,
        )
        elements = []
        elements.append(Paragraph("Отчет о контроле строительных работ", title_style))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"<b>Адрес объекта:</b> {address}", centered_style))
        elements.append(Paragraph(f"<b>Наименование заказчика:</b> {customer}", centered_style))
        elements.append(Paragraph(f"<b>Наименование подрядчика:</b> {contractor}", centered_style))
        elements.append(Paragraph(f"<b>Дата проверки:</b> {check_date}", centered_style))
        elements.append(PageBreak())
        table_data = []
        header = ["№ п/п", "Перечень выявленных нарушений", "Наименование нормативного документа", "Фотоматериал"]
        table_data.append([Paragraph(h, centered_style) for h in header])
        for i, item in enumerate(violations, 1):
            img_buffer = self._numpy_to_image_buffer(item["img"])
            img = ReportLabImage(img_buffer, width=60, height=60)

            table_data.append([
                Paragraph(str(i), centered_style),
                Paragraph(item["description"], centered_style),
                Paragraph("", centered_style),
                img
            ])
        available_width = page_width - doc.leftMargin - doc.rightMargin
        serial_width = 20 * mm
        remaining_width = available_width - serial_width
        desc_width = remaining_width * 0.35
        norm_width = remaining_width * 0.25
        photo_width = remaining_width * 0.40
        col_widths = [serial_width, desc_width, norm_width, photo_width]
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        elements.append(table)
        doc.build(elements)
