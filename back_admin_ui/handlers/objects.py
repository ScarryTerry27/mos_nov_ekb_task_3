import requests
import geocoder
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from services.db import schema
from services.db.db import get_db
from services.db.service import ObjectService, UserService
from services.auth import get_current_user

router = APIRouter(prefix="/objects", tags=["objects"])


@router.post("/", response_model=schema.Object, status_code=status.HTTP_201_CREATED)
def create_object(
        object_in: schema.ObjectCreate,
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin"),
        db: Session = Depends(get_db)
) -> schema.Object:
    # здесь считываем роль пользователя и если она не админ - то не даем создавать объекты - возвращаем ошибку на
    # недостаточность прав
    # так же нужно выполнить проверку всех id в объекте - если данного id не существует - то так же возвращаем ощибку
    # not found на id
    if (not object_in.object_lon or not object_in.object_lat) and object_in.address:
        session = requests.Session()
        session.headers.update({'User-Agent': 'my-app/1.0 (myemail@example.com)'})

        g = geocoder.osm("Москва, планетная 20", session=session)
        object_in.object_lon = g.lng
        object_in.object_lat = g.lat

    current_user = get_current_user(role)
    if current_user.role is not schema.RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    user_service = UserService(db)
    for field_name, user_id in (
            ("admin", object_in.admin_id),
            ("inspector", object_in.inspector_id),
            ("contractor", object_in.contractor_id),
    ):
        if not user_service.get_user_by_id(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{field_name.capitalize()} not found",
            )

    service = ObjectService(db)
    obj = service.create_object(object_in)
    return schema.Object.model_validate(obj)


@router.get("/", response_model=List[schema.Object])
def list_objects(
        db: Session = Depends(get_db),
        user_id: int = Query(..., ge=1),
        limit: int = Query(100, ge=1),
        offset: int = Query(0, ge=0),
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin")
) -> List[schema.Object]:
    # тут мы должны проверить роль пользователя - если он админ то возвращаем все объекты, если нет - то только объекты,
    # связанные с ним
    # так же добавить оффсет и лимит и считывать изначально из бд по офсеты и лимиту, чтобы не переполнять память
    current_user = get_current_user(role)
    current_user.user_id = user_id
    service = ObjectService(db)
    objects = service.list_objects(limit=limit, offset=offset, role=current_user.role, user_id=user_id)
    return [schema.Object.model_validate(obj) for obj in objects]


@router.get("/{object_id}", response_model=schema.Object)
def get_object(
        object_id: int,
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin"),
        db: Session = Depends(get_db)
) -> schema.Object:
    #  здесь так же реализовать проверку если админ - любой объект можно вернуть, если нет - то только объекты,
    #  привязанные к тебе
    # если ты стучишься не будучи админом к объекты, который тебе недоступен - возвращаем нет прав и соот ошибку
    current_user = get_current_user(role)
    current_user.user_id = object_id
    service = ObjectService(db)
    obj = service.get_object(object_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    if current_user.role == schema.RoleEnum.INSPECTOR and obj.inspector_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    if current_user.role == schema.RoleEnum.CONTRACTOR and obj.contractor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    return schema.Object.model_validate(obj)


@router.put("/{object_id}", response_model=schema.Object)
def update_object(
        object_id: int,
        object_in: schema.ObjectUpdate,
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin"),
        db: Session = Depends(get_db)
) -> schema.Object:
    # изменять могут только админы, если стучиться не админ - отправляем ему недостаточность прав

    current_user = get_current_user(role)
    if current_user.role is not schema.RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    user_service = UserService(db)
    for field_name, user_id in (
            ("admin", object_in.admin_id),
            ("inspector", object_in.inspector_id),
            ("contractor", object_in.contractor_id),
    ):
        if user_id is not None and not user_service.get_user_by_id(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{field_name.capitalize()} not found",
            )

    service = ObjectService(db)
    obj = service.update_object(object_id, object_in)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    return schema.Object.model_validate(obj)


@router.delete("/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object(
        object_id: int,
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin"),
        db: Session = Depends(get_db)) -> None:
    # удалять могут только админы, если стучиться не админ - отправляем ему недостаточность прав
    current_user = get_current_user(role)
    if current_user.role is not schema.RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    service = ObjectService(db)
    deleted = service.delete_object(object_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
