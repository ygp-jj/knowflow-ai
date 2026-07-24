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
        3. 更新文档表的 chunk_count 字段（前端轮询文档状态时可见此数字）
        4. 提交数据库事务

    参数 chunks 格式：
        这是由 split_text() 返回的结构，每个元素包含：
            - content: 切片文本内容
            - page_number: 页码（可能为 None）
            - chunk_index: 全局递增序号
            - metadata: 附加信息（可选）

    写入时自动生成：
        - content_hash: 用于内容去重
        - token_count: 估算的 token 数（便于前端做 token 上限控制）
        - vector_id: 暂时为 None，后续由向量化任务填充

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
) -> tuple[list[DocumentChunk], int]:
    """【前端主要调用的查询方法】分页获取某个文档的切片列表。

    前端使用场景：
        当用户在文档详情页点击“查看切片”或“预览分块”时，
        后端 API 调用此函数，按分页返回切片数据。

    返回顺序：
        按 chunk_index 升序排列（0,1,2...），即文档原始阅读顺序。

    返回值：
        - 第一项: 当前页的切片对象列表（包含 content、page_number、chunk_index 等）
        - 第二项: 该文档的切片总数（用于前端计算总页数）

    前端展示建议：
        - 按 chunk_index 依次展示，就是文档的完整内容
        - 如果有 page_number，可以标注“来自第 X 页”
        - 如果没有，说明该文档类型（如 Word/TXT）原本没有分页概念
    """
    query = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id)
    total = query.count()
    items = (
        query.order_by(DocumentChunk.chunk_index.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


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