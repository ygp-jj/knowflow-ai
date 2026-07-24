"""文档管理 HTTP 路由。"""

from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import error_response, success_response
from app.schemas.document import DocumentChunkRead, DocumentCreateRead, DocumentRead, DocumentUpdate
from app.services.chunk_service import list_chunks
from app.services.document_service import (
    create_document,
    delete_document,
    enqueue_document_processing,
    get_document,
    get_download_payload,
    list_documents,
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
):
    """上传文件到 MinIO、创建文档记录，并投递解析切片任务。"""

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
    )
    if document is None:
        return error_response(404, "知识库不存在")

    task_id = enqueue_document_processing(document.id)
    data = DocumentCreateRead.model_validate(document)
    data.task_id = task_id
    return success_response(data)


@router.get("/list")
def list_items(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    knowledge_base_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    """分页查询文档列表，可按知识库过滤。"""

    items, total = list_documents(db, page, page_size, knowledge_base_id)
    data = {
        "items": [DocumentRead.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return success_response(data)


@router.get("/detail")
def detail(id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    """查询文档详情。"""

    document = get_document(db, id)
    if document is None:
        return error_response(404, "文档不存在")

    data = DocumentRead.model_validate(document)
    return success_response(data)


@router.get("/chunks")
def chunks(
    document_id: int = Query(..., gt=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """分页查询文档切片列表。"""

    document = get_document(db, document_id)
    if document is None:
        return error_response(404, "文档不存在")

    items, total = list_chunks(db, document_id, page, page_size)
    data = {
        "items": [DocumentChunkRead.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return success_response(data)


@router.put("/update")
def update(payload: DocumentUpdate, db: Session = Depends(get_db)):
    """更新文档文件名。"""

    document = update_document(db, payload)
    if document is None:
        return error_response(404, "文档不存在")

    data = DocumentRead.model_validate(document)
    return success_response(data)


@router.delete("/delete")
def delete(
    id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    object_storage=Depends(get_object_storage),
):
    """删除文档记录和对应的 MinIO 对象。"""

    deleted = delete_document(db, object_storage, id)
    if not deleted:
        return error_response(404, "文档不存在")

    return success_response()


@router.get("/download")
def download(
    id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    object_storage=Depends(get_object_storage),
):
    """通过后端下载接口返回 MinIO 中的文件流。"""

    document, file_payload = get_download_payload(db, object_storage, id)
    if document is None or file_payload is None:
        return error_response(404, "文档不存在")

    safe_file_name = quote(document.file_name)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{safe_file_name}"}
    return StreamingResponse(
        BytesIO(file_payload["bytes"]),
        media_type=file_payload["content_type"],
        headers=headers,
    )
