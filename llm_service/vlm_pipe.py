import json
import asyncio
from io import BytesIO
from typing import List, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
import base64
import logging

logger = logging.getLogger(__name__)


class CVPipe:
    def __init__(self, llm: ChatOpenAI) -> None:
        self.llm = llm

    async def __call__(self, image_buffer: BytesIO) -> str:
        try:
            encoded_image = await self.encode_image_from_buffer(image_buffer)
            img_type = await self.check_image_type(encoded_image)
            if img_type != "Документ":
                return f"Это не документ, а '{img_type}'."
            doc_text = await self.get_doc_text(encoded_image)
            if not doc_text:
                return "Текст не распознан"
            else:
                return doc_text
        except Exception as e:
            logger.error(f"Ошибка в pipe(): {e}")
            raise

    async def check_image_type(self, encoded_image: str, timeout: int=30) -> str:
        """
        """
        class ImgType(BaseModel):
            image_type: str = Field(
                description="Тип изображения",
                examples=["Документ"],
            )
        try:
            structured_llm = self.llm.with_structured_output(ImgType)
            prompt = (
                "Определи тип изображения. "
                "Если на изображении имеется документ, выведи в ответе 'Документ'."
            )
            messages = [self._get_init_msg(prompt, encoded_image)]
            response = await asyncio.wait_for(
                structured_llm.ainvoke(messages),
                timeout=timeout
            )
            return response.image_type
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при определении типа изображения (>{timeout} сек)")
            raise RuntimeError(f"Таймаут при определении типа изображения (>{timeout} сек)")
        except Exception as e:
            logger.error(f"Ошибка при определении типа изображения: {e}")
            raise RuntimeError(f"Ошибка при определении типа изображения: {e}")

    async def get_doc_text(self, encoded_image: str, timeout: int=90) -> str:
        """
        """
        class Validator(BaseModel):
            doc_type: str = Field(
                description="Тип документа",
                examples=["Товарно-транспортная накладная"]
            )
            doc_number: str = Field(
                description="Номер документа",
                examples=["14665/ТН", "345634"]
            )
            date: str = Field(
                description="Дата документа",
                examples=["15-12-2024"]
            )
            obj_adress: List[str] = Field(
                description="Все адреса грузополучателя. В накладной идут друг за другом.",
                examples=["г. Москва, ул. Луговская, 11", "г. Москва, ш. Кировское, стр. 1"]
            )
            items: List[str] = Field(
                description="Список товаров (работ, услуг), перечисленных в документе, с указанием количества",
                examples=["Бетон, 3 м3, 15.5 т.", "Демонтаж бордюрного камня, 300 п.м."]
            )
            additional_docs: Literal[
                "Паспорт качества",
                "Сертфикат соответствия",
                "-"
            ] = Field(
                description="Перечень прилагающихся документов. Может быть пустым ('-').",
                examples=["Паспорт качества", "Сертфикат соответствия", "-"],
                default="-"
            )
        prompt = """Ты - опытный бухгалтер.
Тебе предоставлен документ строгой отчетности. Определи:
- !!!ОБЯЗАТЕЛЬНО!!! Адреса грузополучателя (юридический адрес и адрес места доставки груза). Они расположены друг за другом.
- Тип документа
- Номер документа
- Дату документа
- Перечень указанного в документе имущества (работ, услуг)
- Перечень прилагающихся сопроводительных документов"""
        try:
            structured_llm = self.llm.with_structured_output(Validator)
            messages = [self._get_init_msg(prompt, encoded_image)]
            response = await asyncio.wait_for(
                structured_llm.ainvoke(messages),
                timeout=timeout
            )
            json_res = json.dumps(response.model_dump(), ensure_ascii=False, indent=0)
            return json_res.strip() if json_res else ""
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при извлечении текста (>{timeout} сек)")
            raise RuntimeError(f"Таймаут при извлечении текста (>{timeout} сек)")
        except Exception as e:
            logger.error(f"Ошибка при извлечении текста из документа: {e}")
            raise RuntimeError(f"Ошибка при извлечении текста: {e}")

    @staticmethod
    def _get_init_msg(prompt: str, encoded_image: str) -> HumanMessage:
        """
        Создаем инициализирующее сообщение для VLLM
        """
        return HumanMessage(
            content=[
                {
                    "type": "text", 
                    "text": prompt
                },
                {
                    "type": "image_url", 
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{encoded_image}"
                    }
                }
            ]
        )

    @staticmethod
    async def encode_image_from_buffer(image_buffer: BytesIO) -> str:
        """
        Кодирует изображение из BytesIO буфера в base64
        """
        encoded_image = base64.b64encode(image_buffer.getvalue()).decode('utf-8')
        return encoded_image
