"""登录鉴权 HTTP 路由：/login、/register（公开）、/me（需 Bearer）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRead, LoginRequest, RegisterRequest, UserRead
from app.schemas.common import error_response, success_response
from app.services.auth_service import AuthServiceError, login, register_user

router = APIRouter()


@router.post("/login")
def auth_login(payload: LoginRequest, db: Session = Depends(get_db)):
    """用户名密码登录，签发 JWT。

    参数:
        payload: username + password。
        db: 数据库会话。
    返回:
        成功时 data 为 { access_token, token_type, user }；失败 code=401。
    """
    try:
        result: LoginRead = login(db, username=payload.username, password=payload.password)
    except AuthServiceError as exc:
        return error_response(exc.http_code, str(exc))
    return success_response(result.model_dump())


@router.post("/register")
def auth_register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """注册新用户并自动登录（返回 Token）。

    参数:
        payload: username + email + password。
        db: 数据库会话。
    返回:
        成功时 data 与 login 相同；冲突时 code=400。
    """
    try:
        result: LoginRead = register_user(
            db,
            username=payload.username,
            email=str(payload.email),
            password=payload.password,
        )
    except AuthServiceError as exc:
        return error_response(exc.http_code, str(exc))
    except Exception as exc:  # noqa: BLE001
        return error_response(500, f"注册失败: {exc}")
    return success_response(result.model_dump())


@router.get("/me")
def auth_me(current_user: User = Depends(get_current_user)):
    """返回当前登录用户信息（需 Bearer）。"""
    return success_response(UserRead.model_validate(current_user).model_dump())
