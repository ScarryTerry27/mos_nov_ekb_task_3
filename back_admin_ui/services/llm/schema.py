from datetime import date
from typing import Literal, List

from pydantic import BaseModel, Field


class ItemsList(BaseModel):
    # OKPD: str = Field(..., description="ОКПД")
    item_name: str = Field(..., description="Наименование")
    UOM: Literal["шт", "м", "м2"] = Field(..., description="ед.измерения")
    amount: float = Field(..., description="Количество")


class Document(BaseModel):
    # object_name: str = Field(..., description="Объект/название объекта")
    # work_area_name: str = Field(..., description="Участок работ")
    doc_name: str = Field(..., description="Транспортная накладная/акт")
    doc_number: str = Field(..., description="Номер документа")
    doc_date_start: date = Field(..., description="Дата документа/Дата начала работ")
    doc_date_end: date = Field(..., description="Дата документа/Дата окончания работ")
    # customer_signatory: str = Field(..., description="заказчик/грузоотправитель/поставщик")
    # executor_signatory: str = Field(..., description="подрядчик/получатель/кладовщик")
    # position_type: Literal["work", "material"] = Field(..., description="Тип позиции")
    item_list: List[ItemsList] = Field(..., description="Список элементов")
