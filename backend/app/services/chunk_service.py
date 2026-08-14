"""文档切片写入与查询服务。

   这个模块管理【文档切片（Chunk）】的数据库操作。
   它和 split_text（切分逻辑）是上下游关系：
        split_text 负责“怎么切”
        这个服务负责“存、查、删”
   前端通过后端 REST API 间接使用这里的功能，主要关注 list_chunks 的返回结果。
"""

import hashlib

from sqlalchemy.orm import Session

from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.token_service import estimate_token_count


def build_content_hash(content: str) -> str:
    """计算切片内容的 SHA-256 哈希值（后端内部去重/变更检测用）。

    前端无需关心这个字段，它不会出现在 API 返回给前端的切片列表中。
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def replace_document_chunks(db: Session, document: Document, chunks: list[dict]) -> list[DocumentChunk]:
    """【核心写入方法】删除文档的全部旧切片，写入新的切片列表。

    调用时机：
        在 Celery 异步任务（process_document）中，split_text 切完后立即调用。
        前端无需主动调用，这是后端内部流程的一部分。

    工作流程（前端可见的副作用）：
        1. 清空该文档在 document_chunks 表中的所有旧记录
        2. 遍历传入的 chunks 列表，逐条写入新记录
        3. 根据 parent_chunk_index 回填 parent_chunk_id（子块挂父块）
        4. 更新文档表的 chunk_count 字段
        5. 提交数据库事务

    参数 chunks 格式：
        这是由 split_text() 返回的结构，每个元素包含：
            - content: 切片文本内容
            - page_number: 页码（可能为 None）
            - chunk_index: 全局递增序号
            - parent_chunk_index: 父块在本次切片列表中的序号（可选）
            - metadata: 附加信息（可选）

    写入时自动生成：
        - content_hash: 用于内容去重
        - token_count: 估算的 token 数（便于前端做 token 上限控制）
        - vector_id: 暂时为 None，后续由向量化任务填充
        - parent_chunk_id: 由 parent_chunk_index 解析为真实主键

    返回：
        新创建的 DocumentChunk 对象列表（含数据库生成的 id 字段）。
    """
    # 1. 删除旧切片（synchronize_session=False 是性能优化，不关心）
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete(synchronize_session=False)

    created_chunks: list[DocumentChunk] = []
    for item in chunks:
        content = item["content"]
        chunk = DocumentChunk(
            document_id=document.id,
            knowledge_base_id=document.knowledge_base_id,
            parent_chunk_id=None,                     # 稍后按 parent_chunk_index 回填
            chunk_index=item["chunk_index"],          # 切片编号（0,1,2...）
            content=content,                          # 切片文本
            content_hash=build_content_hash(content), # 内容指纹（内部用）
            page_number=item.get("page_number"),      # 来源页码（可能 None）
            token_count=estimate_token_count(content),# 估算 token 数
            vector_id=None,                           # 向量 ID（后续异步填充）
            chunk_metadata=item.get("metadata"),      # 附加元数据
        )
        db.add(chunk)
        created_chunks.append(chunk)

    # 先 flush 拿到数据库自增 id，再解析父子关系
    db.flush()
    index_to_id = {chunk.chunk_index: chunk.id for chunk in created_chunks}
    for item, chunk in zip(chunks, created_chunks):
        parent_index = item.get("parent_chunk_index")
        if parent_index is None:
            continue
        parent_id = index_to_id.get(parent_index)
        if parent_id is not None and parent_id != chunk.id:
            chunk.parent_chunk_id = parent_id

    # 2. 更新文档的切片总数（前端展示“该文档已切 X 块”就用这个字段）
    document.chunk_count = len(created_chunks)
    db.commit()

    # 3. 刷新对象（获取数据库生成的 id 等字段）
    for chunk in created_chunks:
        db.refresh(chunk)

    return created_chunks


def list_chunks(
    db: Session,
    document_id: int,
    page: int,
    page_size: int,
    parent_id: int | None = None,
) -> tuple[list[DocumentChunk], int]:
    """【前端主要调用的查询方法】分页获取某个文档的切片列表。

    前端使用场景：
        当用户在文档详情页点击“查看切片”或“预览分块”时，
        后端 API 调用此函数，按分页返回切片数据。

    参数:
        parent_id: 若传入，只返回该父块下的直接子块（命中父块后继续查子块）。

    返回顺序：
        按 chunk_index 升序排列（0,1,2...），即文档原始阅读顺序。

    返回值：
        - 第一项: 当前页的切片对象列表（包含 content、page_number、chunk_index 等）
        - 第二项: 该文档的切片总数（用于前端计算总页数）
    """
    query = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id)
    if parent_id is not None:
        query = query.filter(DocumentChunk.parent_chunk_id == parent_id)
    total = query.count()
    items = (
        query.order_by(DocumentChunk.chunk_index.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def list_child_chunks(db: Session, parent_chunk_id: int) -> list[DocumentChunk]:
    """按父块 ID 拉取全部直接子块（不分页，供检索扩展使用）。"""

    return (
        db.query(DocumentChunk)
        .filter(DocumentChunk.parent_chunk_id == parent_chunk_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )


def expand_chunks_for_retrieval(
    db: Session,
    hit_chunks: list[DocumentChunk],
    *,
    max_depth: int = 2,
) -> list[DocumentChunk]:
    """检索命中后扩展父子块：命中父块则继续并入子块正文。

    规则：
        1. 保留原始命中块顺序
        2. 若命中块下有子块，按 chunk_index 追加子块
        3. 可递归展开（默认 2 层：章→条→分点）
        4. 同一 id 只保留一次
    """

    if not hit_chunks:
        return []

    result: list[DocumentChunk] = []
    seen_ids: set[int] = set()

    def append_unique(chunk: DocumentChunk) -> None:
        if chunk.id in seen_ids:
            return
        seen_ids.add(chunk.id)
        result.append(chunk)

    def expand(chunk: DocumentChunk, depth: int) -> None:
        append_unique(chunk)
        if depth >= max_depth:
            return
        for child in list_child_chunks(db, chunk.id):
            expand(child, depth + 1)

    for hit in hit_chunks:
        expand(hit, 0)
    return result


def clear_document_chunks(db: Session, document_id: int) -> None:
    """【内部工具】删除指定文档的全部切片（不自动提交事务）。

    使用场景：
        当删除整个文档时，作为事务的一部分调用。
        前端无需单独调用，只需调用“删除文档”的 API，后端会联动清理切片。

    注意：
        此函数不执行 db.commit()，由调用方统一控制事务边界。
        如果希望立即生效，调用方需在外部执行 db.commit()。
    """
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete(synchronize_session=False)
