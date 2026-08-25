"""文档管理 HTTP 路由。

文档归属通过知识库 owner_id 隔离：仅当前登录用户自己的知识库下文档可见可操作。
"""

from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import error_response, success_response
from app.schemas.document import (
    DocumentChunkRead,
    DocumentChunkRequest,
    DocumentCreateRead,
    DocumentEmbedRequest,
    DocumentRead,
    DocumentUpdate,
)
from app.services.chunk_service import list_chunks
from app.services.document_service import (
    create_document,
    delete_document,
    get_document,
    get_download_payload,
    list_documents,
    start_document_chunking,
    start_document_embedding,
    update_document,
)
from app.services.object_storage import get_object_storage


router = APIRouter()


@router.post("/create")
async def create(
    knowledge_base_id: int = Form(..., gt=0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    object_storage=Depends(get_object_storage),
    current_user: User = Depends(get_current_user),
):
    """上传文件到 MinIO 并创建文档记录，不自动切片（仅本人知识库）。"""

    file_bytes = await file.read()
    file_name = file.filename or "unnamed-file"
    # MIME 仅用于对象存储；业务 file_type 由服务层从文件名扩展名解析。
    content_type = file.content_type or "application/octet-stream"
    document = create_document(
        db=db,
        object_storage=object_storage,
        knowledge_base_id=knowledge_base_id,
        file_name=file_name,
        file_bytes=file_bytes,
        content_type=content_type,
        owner_id=current_user.id,
    )
    if document is None:
        return error_response(404, "知识库不存在")

    # 上传后保持 uploaded，由前端「切片」按钮手动触发解析。
    data = DocumentCreateRead.model_validate(document)
    data.task_id = None
    return success_response(data)


@router.post("/chunk")
def chunk(
    payload: DocumentChunkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动触发文档解析与切片任务。"""

    document, task_id, error_message = start_document_chunking(
        db, payload.id, owner_id=current_user.id
    )
    if document is None:
        return error_response(404, error_message or "文档不存在")
    if error_message:
        return error_response(400, error_message)

    data = DocumentCreateRead.model_validate(document)
    data.task_id = task_id
    return success_response(data)


@router.post("/embed")
def embed(
    payload: DocumentEmbedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动触发文档向量化（Embedding → Milvus），成功后 status=embedded。"""

    document, task_id, error_message = start_document_embedding(
        db, payload.id, owner_id=current_user.id
    )
    if document is None:
        return error_response(404, error_message or "文档不存在")
    if error_message:
        return error_response(400, error_message)

    data = DocumentCreateRead.model_validate(document)
    data.task_id = task_id
    return success_response(data)


@router.get("/list")
def list_items(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    knowledge_base_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分页查询当前用户知识库下的文档列表，可按知识库过滤。"""

    items, total = list_documents(
        db,
        page,
        page_size,
        knowledge_base_id,
        owner_id=current_user.id,
    )
    data = {
        "items": [DocumentRead.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return success_response(data)


@router.get("/detail")
def detail(
    id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询文档详情（仅本人知识库）。"""

    document = get_document(db, id, owner_id=current_user.id)
    if document is None:
        return error_response(404, "文档不存在")

    data = DocumentRead.model_validate(document)
    return success_response(data)


@router.get("/chunks")
def chunks(
    document_id: int = Query(..., gt=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    parent_id: int | None = Query(default=None, gt=0, description="可选；传入则只返回该父块下的子块"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分页查询文档切片列表（仅本人知识库下的文档）。"""

    document = get_document(db, document_id, owner_id=current_user.id)
    if document is None:
        return error_response(404, "文档不存在")

    items, total = list_chunks(db, document_id, page, page_size, parent_id=parent_id)
    data = {
        "items": [DocumentChunkRead.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return success_response(data)


@router.put("/update")
def update(
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新文档文件名。"""

    document = update_document(db, payload, owner_id=current_user.id)
    if document is None:
        return error_response(404, "文档不存在")

    data = DocumentRead.model_validate(document)
    return success_response(data)


@router.delete("/delete")
def delete(
    id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    object_storage=Depends(get_object_storage),
    current_user: User = Depends(get_current_user),
):
    """删除文档记录和对应的 MinIO 对象。"""

    deleted = delete_document(db, object_storage, id, owner_id=current_user.id)
    if not deleted:
        return error_response(404, "文档不存在")

    return success_response()


@router.get("/download")
def download(
    id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    object_storage=Depends(get_object_storage),
    current_user: User = Depends(get_current_user),
):
    """通过后端下载接口返回 MinIO 中的文件流。"""

    document, file_payload = get_download_payload(
        db, object_storage, id, owner_id=current_user.id
    )
    if document is None or file_payload is None:
        return error_response(404, "文档不存在")

    safe_file_name = quote(document.file_name)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{safe_file_name}"}
    return StreamingResponse(
        BytesIO(file_payload["bytes"]),
        media_type=file_payload["content_type"],
        headers=headers,
    )
