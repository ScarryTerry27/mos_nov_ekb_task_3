from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    ForeignKey,
    Enum,
    Text,
    Float,
    Boolean,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

Base = declarative_base()


class StatusEnum(enum.Enum):
    COMPLETED = "Выполнено"
    IN_PROGRESS = "В работе"
    NOT_STARTED = "Не начато"
    ON_HOLD = "Приостановлено"


class CheckStatusEnum(enum.Enum):
    SUCCESSFUL = "Проверка пройдена"
    INCIDENT = "Инцидент"


class RoleEnum(enum.Enum):
    CONTRACTOR = "contractor"
    INSPECTOR = "inspector"
    ADMIN = "admin"


class PrescriptionTypeEnum(enum.Enum):
    TYPE_1 = "Тип 1"
    TYPE_2 = "Тип 2"


class DocTypeEnum(enum.Enum):
    TTN = "ТТН"
    OUTPUT = "output"


class User(Base):
    __tablename__ = "USER"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    password = Column(String(100), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)


class Object(Base):
    __tablename__ = "OBJECT"

    object_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    admin_id = Column(Integer, ForeignKey("USER.user_id"))
    inspector_id = Column(Integer, ForeignKey("USER.user_id"))
    contractor_id = Column(Integer, ForeignKey("USER.user_id"))

    status = Column(String(50))
    address = Column(String(300))
    # только координаты
    object_lat = Column(Float, nullable=False)
    object_lon = Column(Float, nullable=False)

    admin = relationship("User", foreign_keys=[admin_id])
    inspector = relationship("User", foreign_keys=[inspector_id])
    contractor = relationship("User", foreign_keys=[contractor_id])


class SubObject(Base):
    __tablename__ = "SUBOBJECT"

    subobject_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    object_id = Column(Integer, ForeignKey("OBJECT.object_id"))
    status_inspector = Column(Enum(StatusEnum))
    status_contractor = Column(Enum(StatusEnum))
    status_admin = Column(Enum(StatusEnum))
    prescription_info = Column(Text)
    start_date = Column(Date)
    finish_date = Column(Date)
    object = relationship("Object")


class Check(Base):
    __tablename__ = "CHECK"

    check_id = Column(Integer, primary_key=True, autoincrement=True)
    datetime = Column(DateTime, default=datetime.now)
    info = Column(Text)
    location = Column(Text)
    subobject_id = Column(Integer, ForeignKey("SUBOBJECT.subobject_id"))
    status_check = Column(Enum(CheckStatusEnum))

    subobject = relationship("SubObject")


class Incident(Base):
    __tablename__ = "INCIDENT"

    incident_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=datetime.utcnow)
    check_id = Column(Integer, ForeignKey("CHECK.check_id"))
    photo = Column(Text)
    incident_status = Column(Boolean)
    incident_info = Column(Text)
    prescription_type = Column(Enum(PrescriptionTypeEnum))

    check = relationship("Check")


class Document(Base):
    __tablename__ = "DOCUMENT"

    document_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("USER.user_id"))
    object_id = Column(Integer, ForeignKey("OBJECT.object_id"))
    doc_type = Column(Enum(DocTypeEnum))
    doc_number = Column(String(50))
    doc_date_start = Column(Date)
    doc_date_end = Column(Date)
    doc_image_id = Column(String(100))

    user = relationship("User")
    object = relationship("Object")


class Material(Base):
    __tablename__ = "MATERIAL"

    material_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200))
    doc_id = Column(Integer, ForeignKey("DOCUMENT.document_id"))
    okpd = Column(String(50), nullable=True)
    amount = Column(Float)
    uom = Column(String(20))
    to_be_certified = Column(Boolean)
    certificate = Column(Text)

    document = relationship("Document")
