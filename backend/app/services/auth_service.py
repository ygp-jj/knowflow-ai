"""登录鉴权业务：校验用户名密码、注册并签发 JWT。"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
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


def register_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
) -> LoginRead:
    """注册新用户并自动签发 Token。

    参数:
        db: 数据库会话。
        username: 用户名。
        email: 邮箱。
        password: 明文密码。
    返回:
        与 login 相同的 LoginRead。
    抛出:
        AuthServiceError: 用户名或邮箱已存在。
    """
    username = (username or "").strip()
    email = (email or "").strip().lower()
    if not username:
        raise AuthServiceError("用户名不能为空", http_code=400)
    if db.query(User.id).filter(User.username == username).first() is not None:
        raise AuthServiceError("用户名已存在", http_code=400)
    if db.query(User.id).filter(User.email == email).first() is not None:
        raise AuthServiceError("邮箱已存在", http_code=400)

    now = datetime.now(timezone.utc)
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return build_login_result(user)
