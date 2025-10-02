from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from services.db import schema, model
from services.db.db import get_db
from services.db.service import UserService
from services.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[schema.User])  # ВАЖНО: пустая строка, а не "/"
def list_users(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    role: Optional[schema.RoleEnum] = Query(None, description="Фильтр по роли"),
    name: Optional[str] = Query(
        None, min_length=1, description="Поиск по имени (LIKE)"
    ),
    current=Depends(get_current_user),  # твой TokenPayload
    db: Session = Depends(get_db),
) -> List[schema.User]:
    roles = getattr(current, "roles", None)
    if roles is not None:
        if schema.RoleEnum.ADMIN not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав"
            )
    else:
        # если в токене одна роль
        if getattr(current, "role", None) != schema.RoleEnum.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав"
            )

    # ==== фильтры ====
    role_filter: Optional[model.RoleEnum] = None
    if role is not None:
        # schema.RoleEnum -> model.RoleEnum
        role_filter = model.RoleEnum(role.value)

    service = UserService(db)
    users = service.new_list_users(
        role=role_filter, name=name, limit=limit, offset=offset
    )
    return [schema.User.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=schema.User)
def get_user(
    user_id: int,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schema.User:
    # admin может любого, не-admin — только себя
    is_admin = False
    roles = getattr(current, "roles", None)
    if roles is not None:
        is_admin = schema.RoleEnum.ADMIN in roles
    else:
        is_admin = getattr(current, "role", None) == schema.RoleEnum.ADMIN

    if not is_admin and str(getattr(current, "user_id", "")) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав"
        )

    svc = UserService(db)
    user = svc.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )
    return schema.User.model_validate(user)
