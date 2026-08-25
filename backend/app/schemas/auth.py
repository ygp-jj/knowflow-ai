"""登录鉴权相关请求/响应 Schema。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """登录请求。

    字段:
        username: 用户名。
        password: 明文密码。
    """

    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=1, max_length=128, description="密码")


class RegisterRequest(BaseModel):
    """注册请求。

    字段:
        username: 用户名（唯一）。
        email: 邮箱（唯一）。
        password: 明文密码，至少 6 位。
    """

    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class UserRead(BaseModel):
    """对外暴露的用户信息（不含密码哈希）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    created_at: Optional[datetime] = None


class LoginRead(BaseModel):
    """登录 / 注册成功响应 data。"""

    access_token: str
    token_type: str = "bearer"
    user: UserRead
