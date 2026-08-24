"""登录鉴权业务：校验用户名密码并签发 JWT。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRead, UserRead


class AuthServiceError(RuntimeError):
    """鉴权业务可预期错误。"""

    def __init__(self, message: str, *, http_code: int = 401) -> None:
        super().__init__(message)
        self.http_code = http_code


def authenticate_user(db: Session, *, username: str, password: str) -> User:
    """按用户名密码校验用户。

    参数:
        db: 数据库会话。
        username: 用户名。
        password: 明文密码。
    返回:
        校验通过的 User。
    抛出:
        AuthServiceError: 用户名或密码错误。
    """
    user = db.query(User).filter(User.username == username.strip()).first()
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthServiceError("用户名或密码错误", http_code=401)
    return user


def build_login_result(user: User) -> LoginRead:
    """为已认证用户签发 Token 并组装登录响应。

    参数:
        user: 已通过校验的用户。
    返回:
        LoginRead（含 access_token 与 user）。
    """
    token = create_access_token(subject=user.id, extra_claims={"username": user.username})
    return LoginRead(
        access_token=token,
        token_type="bearer",
        user=UserRead.model_validate(user),
    )


def login(db: Session, *, username: str, password: str) -> LoginRead:
    """登录：校验凭证并返回 Token。

    参数:
        db: 数据库会话。
        username: 用户名。
        password: 明文密码。
    返回:
        LoginRead。
    """
    user = authenticate_user(db, username=username, password=password)
    return build_login_result(user)
