import geocoder
import requests
from fastapi import Request
import datetime
import os
import shutil
import tempfile
from typing import List, Literal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session
from starlette.responses import FileResponse

from services.auth import get_current_user
from services.db import schema
from services.db.db import get_db
from services.db.model import SubObject
from services.db.service import CheckService, IncidentService, ObjectService, SubObjectService
from services.others.video_client import VideoPipe, ReportGenerator
from utils import haversine_km

router = APIRouter(prefix="/checks", tags=["checks"])

REPORTS_DIR = Path("reports")


def _ensure_subobject_access(
        db: Session, subobject_id: int, current_user: schema.User
) -> None:
    subobject_service = SubObjectService(db)
    subobject = subobject_service.get_subobject(subobject_id)
    if not subobject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subobject not found"
        )

    if current_user.role == schema.RoleEnum.INSPECTOR:
        object_service = ObjectService(db)
        parent_object = object_service.get_object(subobject.object_id)
        if not parent_object:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Object not found"
            )
        # if parent_object.inspector_id != current_user.user_id:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Insufficient permissions",
        #     )


@router.post("/", response_model=schema.Check, status_code=status.HTTP_201_CREATED)
def create_check(
        check_in: schema.CheckCreate,
        role: Literal["admin", "inspector", "contractor"] = Query(default="inspector"),
        db: Session = Depends(get_db)
) -> schema.Check:
    # только админы и instructor юзерам не видно
    # так же реализовать проверки обзяательных полей
    # реализовать проверку что instructor имеет доступ к данной проверке и субобъекту
    current_user = get_current_user(role)
    if current_user.role not in (schema.RoleEnum.ADMIN, schema.RoleEnum.INSPECTOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    _ensure_subobject_access(db, check_in.subobject_id, current_user)

    service = CheckService(db)
    check = service.create_check(check_in)
    return schema.Check.model_validate(check)


@router.get("/", response_model=List[schema.Check])
def list_checks(
        subobject_id: int = Query(..., ge=1),
        limit: int = Query(100, ge=1),
        offset: int = Query(0, ge=0),
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin"),
        db: Session = Depends(get_db),
) -> List[schema.Check]:
    # только не юзерам - при этом показываем админу все проверки, а instructor его проверки
    # так же реализовать проверку полей и id
    # реализовать проверку что instructor имеет доступ к данной проверке и субобъекту
    current_user = get_current_user(role)
    if current_user.role not in (schema.RoleEnum.ADMIN, schema.RoleEnum.INSPECTOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    _ensure_subobject_access(db, subobject_id, current_user)

    service = CheckService(db)
    checks = service.list_checks(
        subobject_id=subobject_id,
        limit=limit,
        offset=offset,
        role=current_user.role,
        user_id=current_user.user_id,
    )
    return [schema.Check.model_validate(item) for item in checks]


@router.get("/{check_id}", response_model=schema.Check)
def get_check(
        check_id: int,
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin"),
        db: Session = Depends(get_db)) -> schema.Check:
    # только не юзерам
    # реализовать проверку обязательных полей
    # реализовать проверку что instructor имеет доступ к данной проверке и субобъекту
    current_user = get_current_user(role)
    if current_user.role not in (schema.RoleEnum.ADMIN, schema.RoleEnum.INSPECTOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    service = CheckService(db)
    check = service.get_check(check_id)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check not found")
    _ensure_subobject_access(db, check.subobject_id, current_user)
    return schema.Check.model_validate(check)


@router.put("/{check_id}", response_model=schema.Check)
def update_check(
        check_id: int,
        check_in: schema.CheckUpdate,
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin"),
        db: Session = Depends(get_db)
) -> schema.Check:
    # только не юзерам так же реализовать проверку что instructor имеет доступ к данной проверке и субобъекту
    current_user = get_current_user(role)
    if current_user.role not in (schema.RoleEnum.ADMIN, schema.RoleEnum.INSPECTOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    service = CheckService(db)
    existing_check = service.get_check(check_id)
    if not existing_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check not found")
    _ensure_subobject_access(db, existing_check.subobject_id, current_user)

    if "subobject_id" in check_in.model_fields_set:
        _ensure_subobject_access(db, check_in.subobject_id, current_user)

    check = service.update_check(check_id, check_in)
    return schema.Check.model_validate(check)


@router.delete("/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_check(
        check_id: int,
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin"),
        db: Session = Depends(get_db)) -> None:
    # только админ
    current_user = get_current_user(role)
    if current_user.role is not schema.RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    service = CheckService(db)
    deleted = service.delete_check(check_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check not found")


@router.post(
    "/process-video",
    # response_model=schema.VideoProcessingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def process_video(
        request: Request,
        role: Literal["admin", "inspector", "contractor"] = Query(default="inspector"),
        subobject_id: int = Form(...),
        video: UploadFile = File(...),
        location_lat: float = Form(None),
        location_lon: float = Form(None),
        address: str = Form(None),
        db: Session = Depends(get_db),
):  # -> schema.VideoProcessingResponse
    """Accept a video, forward it to the analysis service and persist results."""
    current_user = get_current_user(role)
    if current_user.role is not schema.RoleEnum.INSPECTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only inspectors are allowed to process videos"
        )

    if subobject_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sub_object_id must be a positive integer")

    if video.content_type not in {"video/mp4", "video/mpeg", "video/quicktime"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only MP4, MPEG and QuickTime are allowed.",
        )

    _ensure_subobject_access(db, subobject_id, current_user)

    # достаём объект
    subobj = db.query(SubObject).filter(SubObject.subobject_id == subobject_id).first()
    if not subobj or not subobj.object:
        raise HTTPException(status_code=404, detail="Subobject or parent object not found")

    if (not location_lon or not location_lat) and address:
        session = requests.Session()
        session.headers.update({'User-Agent': 'my-app/1.0 (myemail@example.com)'})

        g = geocoder.osm("Москва, планетная 20", session=session)
        location_lon = g.lng
        location_lat = g.lat
    if not location_lon or not location_lat and not address:
        raise HTTPException(status_code=400, detail="Either location coordinates or address must be provided")

    obj = subobj.object
    obj_lat, obj_lon = float(obj.object_lat), float(obj.object_lon)

    # проверка радиуса
    dist = haversine_km(float(location_lat), float(location_lon), obj_lat, obj_lon)
    if dist > 1.0:
        raise HTTPException(status_code=400, detail=f"Location outside allowed radius ({dist:.2f} km > 1.00 km)")

    suffix = {
        "video/mp4": ".mp4",
        "video/mpeg": ".mpeg",
        "video/quicktime": ".mov",
    }.get(video.content_type, ".mp4")

    tmp_path = None
    try:
        # сохраняем входящее видео на диск во временный файл
        await video.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            # копируем весь поток корректно (без потери байт)
            video.file.seek(0)
            shutil.copyfileobj(video.file, tmp)
            tmp.flush()
            os.fsync(tmp.fileno())

        # Параметры LLM — оставлены как у вас
        params = {
            "model": "deepseek-chat",
            "openai_api_base": "https://api.deepseek.com/v1",
            "openai_api_key": os.getenv("DEEPSEEK_API_KEY"),
            "temperature": 0,
            "max_tokens": None,
            "timeout": None,
            "max_retries": 2
        }

        llm = ChatOpenAI(**params)
        pipe = VideoPipe(llm, trr_serv_url=os.getenv("TRANSCRIBE_URL"))

        # Вызываем пайп ОДИН раз, передаём путь до файла (str)
        result = await pipe(tmp_path)
        if not result or not isinstance(result, tuple):
            raise HTTPException(status_code=502, detail="Video analysis failed")

        info, incidents = result  # info: list[dict], incidents: list[dict]
        text_info = "\n".join(i.get("text", "") for i in info)  # прогонять через ллм и придавать ему нормальный вид

        check_create = schema.CheckCreate(
            subobject_id=subobject_id,
            incident_status=bool(incidents),
            info=text_info,
            location=None
        )

        check_service = CheckService(db)
        incident_service = IncidentService(db)

        created_check = check_service.create_check(check_create)
        saved_incidents: list[schema.Incident] = []

        for incident_data in incidents:
            img = incident_data.get("img") if isinstance(incident_data, dict) else getattr(incident_data, "img", None)
            desc = incident_data.get("description") if isinstance(incident_data, dict) else getattr(
                incident_data, "description", None)

            incident = incident_service.create_incident(schema.IncidentCreate(
                check_id=created_check.check_id,
                photo=str(img),
                incident_info=desc or "",
                incident_status=True,
            ))
            saved_incidents.append(schema.Incident.model_validate(incident))

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / f"{created_check.check_id}.pdf"

        # 2) Генерим PDF именно туда
        rg = ReportGenerator()
        rg.create_report(
            str(report_path),
            address="Адрес объекта",
            customer=subobj.object.admin,
            contractor=subobj.object.contractor,
            check_date=str(datetime.datetime.now()),
            violations=incidents
        )

        # 3) Возвращаем прежний JSON + корректный URL для скачивания
        return {
            "check": schema.Check.model_validate(created_check),
            "incidents": saved_incidents,
            "report_url": request.url_for("download_report", check_id=created_check.check_id)
        }

    finally:
        # Чистим временный файл
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


@router.get("/reports/{check_id}.pdf")
def download_report(check_id: int):
    path = f"reports/{check_id}.pdf"
    if not os.path.exists(path):
        raise HTTPException(404, "Report not found")
    return FileResponse(path, filename=f"report_{check_id}.pdf", media_type="application/pdf")
