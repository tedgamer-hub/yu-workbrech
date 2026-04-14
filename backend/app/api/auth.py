from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.security import create_access_token, verify_password

router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class AuthUserResponse(BaseModel):
    id: int
    username: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: AuthUserResponse


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    token = create_access_token(subject=str(user.id), username=user.username, role=user.role)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=AuthUserResponse(id=user.id, username=user.username, role=user.role),
    )


@router.get("/me", response_model=AuthUserResponse)
def me(current_user: User = Depends(get_current_user)) -> AuthUserResponse:
    return AuthUserResponse(id=current_user.id, username=current_user.username, role=current_user.role)