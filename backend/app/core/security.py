"""密码哈希与 JWT 签发/校验。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# 密码哈希上下文（bcrypt）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """对明文密码做 bcrypt 哈希。

    参数:
        plain_password: 明文密码。
    返回:
        bcrypt 哈希字符串。
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希是否匹配。

    参数:
        plain_password: 明文密码。
        hashed_password: 库中存储的哈希。
    返回:
        匹配为 True，否则 False。
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:  # noqa: BLE001 — 非法哈希等视为校验失败
        return False


def create_access_token(*, subject: str | int, extra_claims: dict[str, Any] | None = None) -> str:
    """签发访问 Token。

    参数:
        subject: JWT sub，一般为用户 id。
        extra_claims: 可选附加声明。
    返回:
        编码后的 JWT 字符串。
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=int(settings.jwt_expire_minutes))
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": expire,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """解码并校验 JWT。

    参数:
        token: Bearer Token 字符串。
    返回:
        payload 字典。
    抛出:
        JWTError: 签名无效、过期或格式错误。
    """
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
