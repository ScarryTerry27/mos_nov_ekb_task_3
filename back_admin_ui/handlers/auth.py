from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from services.db import schema
from services.db.db import get_db
from services.db.service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schema.User, status_code=status.HTTP_201_CREATED)
def register_user(user_in: schema.UserCreate, db: Session = Depends(get_db)) -> schema.User:
    service = UserService(db)

    existing_user = service.get_user_by_name(user_in.name)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    user = service.create_user(user_in)
    return schema.User.model_validate(user)


@router.post("/login", response_model=schema.User)
def login_user(credentials: schema.UserLogin, db: Session = Depends(get_db)) -> schema.User:
    service = UserService(db)

    user = service.authenticate(credentials.name, credentials.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return schema.User.model_validate(user)


@router.post("/forgot-password", response_model=schema.User)
def forgot_password(payload: schema.PasswordResetRequest, db: Session = Depends(get_db)) -> schema.User:
    service = UserService(db)

    user = service.get_user_by_name(payload.name)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updated_user = service.update_password(user.user_id, payload.new_password)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to update password")

    return schema.User.model_validate(updated_user)
