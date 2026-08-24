"""知识库管理业务服务。

本模块封装知识库 CRUD 规则，路由层只负责调用这些函数。
owner_id 由 JWT 当前用户注入，不由前端传入。
"""

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate


def create_knowledge_base(
    db: Session,
    payload: KnowledgeBaseCreate,
    *,
    owner_id: int,
) -> KnowledgeBase:
    """创建知识库。

    参数:
        db: 数据库会话。
        payload: 创建请求数据，包含知识库名称、描述。
        owner_id: 所属用户 ID（来自 JWT）。
    返回:
        已写入数据库并刷新后的 KnowledgeBase 实例。
    """

    knowledge_base = KnowledgeBase(
        name=payload.name,
        description=payload.description,
        owner_id=owner_id,
    )
    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base


def list_knowledge_bases(db: Session, owner_id: int, page: int, page_size: int) -> tuple[list[KnowledgeBase], int]:
    """分页查询指定用户的知识库。

    参数:
        db: 数据库会话。
        owner_id: 所属用户 ID。
        page: 当前页码，从 1 开始。
        page_size: 每页数量。
    返回:
        items 为当前页知识库列表，total 为符合条件的总数量。
    """

    query = db.query(KnowledgeBase).filter(KnowledgeBase.owner_id == owner_id)
    total = query.count()
    items = (
        query.order_by(KnowledgeBase.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_knowledge_base(db: Session, knowledge_base_id: int, owner_id: int) -> KnowledgeBase | None:
    """按 ID 和所属用户查询知识库。

    参数:
        db: 数据库会话。
        knowledge_base_id: 知识库 ID。
        owner_id: 所属用户 ID。
    返回:
        找到时返回 KnowledgeBase，否则返回 None。
    """

    return (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.id == knowledge_base_id, KnowledgeBase.owner_id == owner_id)
        .first()
    )


def update_knowledge_base(
    db: Session,
    payload: KnowledgeBaseUpdate,
    *,
    owner_id: int,
) -> KnowledgeBase | None:
    """更新知识库。

    参数:
        db: 数据库会话。
        payload: 更新请求数据，包含 id、name、description。
        owner_id: 所属用户 ID（来自 JWT）。
    返回:
        更新后的 KnowledgeBase；目标不存在时返回 None。
    """

    knowledge_base = get_knowledge_base(db, payload.id, owner_id)
    if knowledge_base is None:
        return None

    knowledge_base.name = payload.name
    knowledge_base.description = payload.description
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base


def has_documents(db: Session, knowledge_base_id: int) -> bool:
    """判断知识库下是否存在文档。

    参数:
        db: 数据库会话。
        knowledge_base_id: 知识库 ID。
    返回:
        存在任意关联文档时返回 True。
    """

    return db.query(Document.id).filter(Document.knowledge_base_id == knowledge_base_id).first() is not None


def delete_knowledge_base(db: Session, knowledge_base_id: int, owner_id: int) -> str:
    """删除空知识库，返回业务结果状态。

    参数:
        db: 数据库会话。
        knowledge_base_id: 知识库 ID。
        owner_id: 所属用户 ID。
    返回:
        deleted 表示删除成功，not_found 表示不存在，has_documents 表示存在关联文档。
    """

    knowledge_base = get_knowledge_base(db, knowledge_base_id, owner_id)
    if knowledge_base is None:
        return "not_found"
    if has_documents(db, knowledge_base_id):
        return "has_documents"

    db.delete(knowledge_base)
    db.commit()
    return "deleted"
