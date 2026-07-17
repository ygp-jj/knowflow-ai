"""知识库管理 HTTP 路由。

本模块只处理请求参数、数据库依赖注入和统一响应包装；
具体 CRUD 业务放在 app.services.knowledge_base_service 中。
owner_id 由前端通过请求参数传入，不再在服务层硬编码。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import error_response, success_response
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseRead, KnowledgeBaseUpdate
from app.services.knowledge_base_service import (
    create_knowledge_base,
    delete_knowledge_base,
    get_knowledge_base,
    list_knowledge_bases,
    update_knowledge_base,
)


router = APIRouter()


@router.post("/create")
def create(payload: KnowledgeBaseCreate, db: Session = Depends(get_db)):
    """创建知识库。

    参数:
        payload: 创建知识库请求体，包含 name、description、owner_id。
        db: FastAPI 注入的数据库会话。
    返回:
        统一响应结构，data 为创建后的知识库信息。
    """

    knowledge_base = create_knowledge_base(db, payload)
    data = KnowledgeBaseRead.model_validate(knowledge_base)

    return success_response(data)


@router.get("/list")
def list_items(
    owner_id: int = Query(..., gt=0, description="所属用户 ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """分页查询知识库列表。

    参数:
        owner_id: 所属用户 ID，必填。
        page: 当前页码，从 1 开始。
        page_size: 每页数量，限制在 1 到 100 之间。
        db: FastAPI 注入的数据库会话。
    返回:
        统一响应结构，data 包含 items、total、page、page_size。
    """

    items, total = list_knowledge_bases(db, owner_id, page, page_size)
    data = {
        "items": [KnowledgeBaseRead.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return success_response(data)


@router.get("/detail")
def detail(
    id: int = Query(..., gt=0),
    owner_id: int = Query(..., gt=0, description="所属用户 ID"),
    db: Session = Depends(get_db),
):
    """查询知识库详情。

    参数:
        id: 查询参数传入的知识库 ID，不放在 URL 路径段里。
        owner_id: 所属用户 ID。
        db: FastAPI 注入的数据库会话。
    返回:
        统一响应结构；知识库不存在时返回 code=404。
    """

    knowledge_base = get_knowledge_base(db, id, owner_id)
    if knowledge_base is None:
        return error_response(404, "知识库不存在")

    data = KnowledgeBaseRead.model_validate(knowledge_base)
    return success_response(data)


@router.put("/update")
def update(payload: KnowledgeBaseUpdate, db: Session = Depends(get_db)):
    """更新知识库。

    参数:
        payload: 更新知识库请求体，包含 id、name、description、owner_id。
        db: FastAPI 注入的数据库会话。
    返回:
        统一响应结构；知识库不存在时返回 code=404。
    """

    knowledge_base = update_knowledge_base(db, payload)
    if knowledge_base is None:
        return error_response(404, "知识库不存在")

    data = KnowledgeBaseRead.model_validate(knowledge_base)
    return success_response(data)


@router.delete("/delete")
def delete(
    id: int = Query(..., gt=0),
    owner_id: int = Query(..., gt=0, description="所属用户 ID"),
    db: Session = Depends(get_db),
):
    """删除空知识库。

    参数:
        id: 查询参数传入的知识库 ID，不放在 URL 路径段里。
        owner_id: 所属用户 ID。
        db: FastAPI 注入的数据库会话。
    返回:
        统一响应结构；存在关联文档时返回 code=400 并拒绝删除。
    """

    result = delete_knowledge_base(db, id, owner_id)
    if result == "not_found":
        return error_response(404, "知识库不存在")
    if result == "has_documents":
        return error_response(400, "知识库下存在文档，不能删除")

    return success_response()
