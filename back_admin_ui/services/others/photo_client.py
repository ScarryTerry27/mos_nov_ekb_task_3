import os

from services.db import schema
import json
import httpx
from uuid import uuid4
from datetime import datetime, date, timedelta
from typing import Tuple, List, Optional

# Маппинг русских типовых названий документа -> ваш DocTypeEnum
DOC_TYPE_MAP = {
    "ТОВАРНО-ТРАНСПОРТНАЯ НАКЛАДНАЯ": schema.DocTypeEnum.TTN,
    "ДОКУМЕНТ О КАЧЕСТВЕ БЕТОНОВОЙ СМЕСИ": getattr(schema.DocTypeEnum, "QUALITY_DOC", schema.DocTypeEnum.TTN),
    "ПАСПОРТ КАЧЕСТВА": getattr(schema.DocTypeEnum, "CERTIFICATE", schema.DocTypeEnum.TTN),
}


def _parse_date_ddmmyyyy(s: str) -> Optional[date]:
    try:
        return datetime.strptime(s.strip(), "%d.%m.%Y").date()
    except Exception:
        return None


def _map_doc_type(value: Optional[str]) -> schema.DocTypeEnum:
    if not value:
        return schema.DocTypeEnum.TTN  # дефолт, если сервис не прислал
    key = value.strip().upper()
    return DOC_TYPE_MAP.get(key, getattr(schema.DocTypeEnum, "OTHER", schema.DocTypeEnum.TTN))


def _infer_to_be_certified(additional_docs: Optional[str]) -> bool:
    if not additional_docs:
        return False
    s = additional_docs.lower()
    return "паспорт качества" in s or "сертификат" in s


async def analyze_photo(
        image_bytes: bytes,
        filename: str,
        content_type: str
) -> Tuple[schema.DocumentBase, List[schema.MaterialBase]]:
    """
    Отправляем фото на внешний сервис /upload-image и маппим ответ в (DocumentBase, [MaterialBase]).
    Ожидаемый ответ сервиса:
    {
      "result": "{...json-string...}"  # как в примере пользователя
      # ИЛИ сразу {...}
    }
    """
    url = os.getenv("TRANSCRIBE_URL2")
    files = {
        "file": (filename or "photo.jpg", image_bytes, content_type or "image/jpeg"),
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, files=files, headers={"accept": "application/json"})
        resp.raise_for_status()
        payload = resp.json()

    # У сервиса "result" может быть строкой-JSON (как в примере) — поддерживаем оба случая
    raw = payload.get("result", payload)
    if isinstance(raw, str):
        data = json.loads(raw)
    else:
        data = raw

    # Извлекаем поля из ответа сервиса
    doc_type_ru: Optional[str] = data.get("doc_type")
    doc_number: Optional[str] = data.get("doc_number")
    date_str: Optional[str] = data.get("date")  # "03.08.2025"
    # obj_adress: list[str] = data.get("obj_adress", [])    # сейчас не складываем в БД, но можно сохранить в метаданные
    items: List[str] = data.get("items", [])  # материалы по одному названию
    additional_docs: Optional[str] = data.get("additional_docs")

    # Преобразования
    doc_type = _map_doc_type(doc_type_ru)
    doc_date_start = _parse_date_ddmmyyyy(date_str) or date.today()
    # если дата окончания в документе не приходит — зададим rule-of-thumb +30 дней
    doc_date_end = doc_date_start + timedelta(days=30)

    # В вашем Document есть doc_image_id — сгенерируем, если внешний сервис не даёт ID
    doc_image_id = uuid4().hex

    # Собираем DocumentBase под вашу схему
    document_data = schema.DocumentBase(
        doc_type=doc_type,
        doc_number=doc_number or f"DOC-{uuid4().hex[:8].upper()}",
        doc_date_start=doc_date_start,
        doc_date_end=doc_date_end,
        doc_image_id=doc_image_id,
    )

    # Собираем материалы из items
    to_be_certified = _infer_to_be_certified(additional_docs)
    materials_data: List[schema.MaterialBase] = []
    for name in items or []:
        materials_data.append(
            schema.MaterialBase(
                name=name,
                okpd=None,  # сервис не вернул; можно будет дообогащать позже
                amount=1.0,  # нет количества — ставим 1
                uom="шт",  # единица измерения по умолчанию
                to_be_certified=to_be_certified,
                certificate=additional_docs or None,
            )
        )

    # Если сервис не вернул items, но есть "Паспорт качества", можно создать один материал-заглушку:
    if not materials_data and additional_docs:
        materials_data.append(
            schema.MaterialBase(
                name="Материал (из паспорта качества)",
                okpd=None,
                amount=1.0,
                uom="шт",
                to_be_certified=True,
                certificate=additional_docs,
            )
        )

    return document_data, materials_data
