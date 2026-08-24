"""登录鉴权 HTTP 路由：/login（公开）、/me（需 Bearer）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRead, LoginRequest, UserRead
from app.schemas.common import error_response, success_response
from app.services.auth_service import AuthServiceError, login

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


@router.get("/me")
def auth_me(current_user: User = Depends(get_current_user)):
    """返回当前登录用户信息（需 Bearer）。"""
    return success_response(UserRead.model_validate(current_user).model_dump())
