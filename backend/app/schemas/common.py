"""通用响应 Schema 和响应构造函数。"""

from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    """统一接口响应结构。

    字段:
        code: 业务状态码，0 表示成功。
        message: 业务提示信息。
        data: 响应数据，错误时为 None。
    """

    code: int
    message: str
    data: Any = None


def success_response(data: Any = None) -> dict:
    """构造成功响应。

    参数:
        data: 成功时返回给前端的数据。
    返回:
        符合统一响应格式的 dict。
    """

    return {"code": 0, "message": "success", "data": data}


def error_response(code: int, message: str) -> dict:
    """构造业务错误响应。

    参数:
        code: 业务错误码。
        message: 前端可展示的错误信息。
    返回:
        data 固定为 None 的统一响应 dict。
    """

    return {"code": code, "message": message, "data": None}
