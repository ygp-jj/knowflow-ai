"""测试用鉴权工具：签发 Bearer Token。"""

from __future__ import annotations

from app.core.security import create_access_token, hash_password


DEMO_PASSWORD = "demo123456"


def hashed_demo_password() -> str:
    """演示密码 demo123456 的 bcrypt 哈希。"""
    return hash_password(DEMO_PASSWORD)


def auth_header_for_user(user_id: int, *, username: str | None = None) -> dict[str, str]:
    """构造 Authorization Bearer 请求头。

    参数:
        user_id: JWT sub。
        username: 可选写入 claim。
    返回:
        {"Authorization": "Bearer ..."}.
    """
    extra = {"username": username} if username else None
    token = create_access_token(subject=user_id, extra_claims=extra)
    return {"Authorization": f"Bearer {token}"}
