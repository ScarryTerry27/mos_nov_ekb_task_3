from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from services.db import schema
from services.db.db import get_db
from services.db.service import ObjectService, SubObjectService
from services.auth import get_current_user

router = APIRouter(prefix="/subobjects", tags=["subobjects"])


@router.post("/", response_model=schema.SubObject, status_code=status.HTTP_201_CREATED)
def create_subobject(
        subobject_in: schema.SubObjectCreate,
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin"),
        db: Session = Depends(get_db)
) -> schema.SubObject:
    current_user = get_current_user(role)
    if current_user.role is not schema.RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    object_service = ObjectService(db)
    if not object_service.get_object(subobject_in.object_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object not found"
        )

    service = SubObjectService(db)
    subobject = service.create_subobject(subobject_in)

    return schema.SubObject.model_validate(subobject)


@router.get("/", response_model=schema.SubObjectListResponse)
def list_subobjects(
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin"),
        object_id: int = Query(..., ge=1),
        limit: int = Query(100, ge=1),
        offset: int = Query(0, ge=0),
        db: Session = Depends(get_db),
) -> schema.SubObjectListResponse:
    # Ситуация как в объекте - возвращем админу все с оффсетом и лимитом, остальным только их проекты
    current_user = get_current_user(role)
    object_service = ObjectService(db)
    parent_object = object_service.get_object(object_id)
    if not parent_object:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object not found"
        )

    if (
            current_user.role == schema.RoleEnum.INSPECTOR
            and parent_object.inspector_id != current_user.user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    if (
            current_user.role == schema.RoleEnum.CONTRACTOR
            and parent_object.contractor_id != current_user.user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    service = SubObjectService(db)
    subobjects = service.list_subobjects(
        object_id=object_id,
        limit=limit,
        offset=offset,
        role=current_user.role,
        user_id=current_user.user_id,
    )
    return schema.SubObjectListResponse(
        object=schema.Object.model_validate(parent_object),
        subobjects=[schema.SubObject.model_validate(item) for item in subobjects],
    )


@router.get("/{subobject_id}", response_model=schema.SubObject)
def get_subobject(
        subobject_id: int,
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin"),
        db: Session = Depends(get_db)) -> schema.SubObject:
    current_user = get_current_user(role)
    service = SubObjectService(db)
    subobject = service.get_subobject(subobject_id)
    if not subobject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subobject not found"
        )
    if current_user.role in (schema.RoleEnum.INSPECTOR, schema.RoleEnum.CONTRACTOR):
        object_service = ObjectService(db)
        parent_object = object_service.get_object(subobject.object_id)
        if not parent_object:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Object not found"
            )
        if (
                current_user.role == schema.RoleEnum.INSPECTOR
                and parent_object.inspector_id != current_user.user_id
        ) or (
                current_user.role == schema.RoleEnum.CONTRACTOR
                and parent_object.contractor_id != current_user.user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
    return schema.SubObject.model_validate(subobject)


@router.put("/{subobject_id}", response_model=schema.SubObject)
def update_subobject(
        subobject_id: int,
        subobject_in: schema.SubObjectUpdate,
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin"),
        db: Session = Depends(get_db),
) -> schema.SubObject:
    # так же как в объекте - только апдейтить может еще instructor - свое поле статус инструктор -
    # статус админ если мелькает от инспектора - возвращаем отсутствие прав
    # апдейтить может и конструктор - только свой статус, если он пытается обновить статус у других ролей - возвращаем
    # недостаточность прав
    current_user = get_current_user(role)
    allowed_fields = set()

    if current_user.role == schema.RoleEnum.ADMIN:
        allowed_fields = {
            "name",
            "status_inspector",
            "status_contractor",
            "status_admin",
            "prescription_info",
            "object_id",
        }
    elif current_user.role == schema.RoleEnum.INSPECTOR:
        allowed_fields = {"status_inspector"}
    elif current_user.role == schema.RoleEnum.CONTRACTOR:
        allowed_fields = {"status_contractor"}
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    requested_fields = set(subobject_in.model_fields_set)
    if requested_fields and not requested_fields.issubset(allowed_fields):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update requested fields",
        )

    service = SubObjectService(db)
    existing_subobject = service.get_subobject(subobject_id)
    if not existing_subobject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subobject not found"
        )

    if current_user.role in (schema.RoleEnum.INSPECTOR, schema.RoleEnum.CONTRACTOR):
        object_service = ObjectService(db)
        parent_object = object_service.get_object(existing_subobject.object_id)
        if not parent_object:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Object not found"
            )
        if (
                current_user.role == schema.RoleEnum.INSPECTOR
                and parent_object.inspector_id != current_user.user_id
        ) or (
                current_user.role == schema.RoleEnum.CONTRACTOR
                and parent_object.contractor_id != current_user.user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )

    if "object_id" in requested_fields:
        object_service = ObjectService(db)
        if not object_service.get_object(subobject_in.object_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Object not found"
            )

    subobject = service.update_subobject(subobject_id, subobject_in)
    if not subobject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subobject not found"
        )
    return schema.SubObject.model_validate(subobject)


@router.delete("/{subobject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subobject(
        subobject_id: int,
        role: Literal["admin", "inspector", "contractor"] = Query(default="admin"),
        db: Session = Depends(get_db)) -> None:
    # так же как в объекте - удалять может только админ
    current_user = get_current_user(role)
    if current_user.role is not schema.RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    service = SubObjectService(db)
    deleted = service.delete_subobject(subobject_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subobject not found"
        )
