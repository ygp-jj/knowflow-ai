"""文档管理接口单测。"""

import io
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.chunk import DocumentChunk  # noqa: F401
from app.models.document import Document
from app.models.user import User


class FakeObjectStorage:
    """内存对象存储假实现，用于隔离 MinIO 依赖。"""

    def __init__(self):
        self.objects = {}

    def upload_file(self, file_bytes: bytes, object_name: str, content_type: str):
        self.objects[object_name] = {"bytes": file_bytes, "content_type": content_type}
        return object_name

    def download_file(self, object_name: str):
        return self.objects.get(object_name)

    def delete_file(self, object_name: str):
        self.objects.pop(object_name, None)


class DocumentsApiTests(unittest.TestCase):
    def setUp(self):
        from app.api.v1.documents import get_object_storage
        from app.models.knowledge_base import KnowledgeBase

        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        owner_id = 101

        db = self.SessionLocal()
        db.add(User(id=owner_id, username="default", email="default@example.com", hashed_password="test"))
        db.add(KnowledgeBase(id=1, name="默认知识库", description="测试用", owner_id=owner_id))
        db.commit()
        db.close()

        self.fake_storage = FakeObjectStorage()
        self.enqueue_patcher = patch(
            "app.services.document_service.enqueue_document_processing",
            return_value="fake-task-id",
        )
        self.mock_enqueue = self.enqueue_patcher.start()
        self.embed_enqueue_patcher = patch(
            "app.services.document_service.enqueue_document_embedding",
            return_value="fake-embed-task-id",
        )
        self.mock_embed_enqueue = self.embed_enqueue_patcher.start()
        # 删除文档会 best-effort 清 Milvus；单测不连真实服务，避免超时拖慢
        self.milvus_patcher = patch("app.services.milvus_service.get_milvus_service")
        self.mock_milvus = self.milvus_patcher.start()
        self.mock_milvus.return_value.delete_by_document_id.return_value = None

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        def override_get_object_storage():
            return self.fake_storage

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_object_storage] = override_get_object_storage
        self.client = TestClient(app)

    def tearDown(self):
        self.milvus_patcher.stop()
        self.embed_enqueue_patcher.stop()
        self.enqueue_patcher.stop()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)

    def test_create_list_detail_update_download_delete_document(self):
        create_response = self.client.post(
            "/api/v1/documents/create",
            data={"knowledge_base_id": "1"},
            files={"file": ("product.pdf", io.BytesIO(b"pdf-content"), "application/pdf")},
        )

        self.assertEqual(create_response.status_code, 200)
        create_body = create_response.json()
        self.assertEqual(create_body["code"], 0)
        self.assertEqual(create_body["message"], "success")
        self.assertEqual(create_body["data"]["knowledge_base_id"], 1)
        self.assertEqual(create_body["data"]["file_name"], "product.pdf")
        self.assertEqual(create_body["data"]["status"], "uploaded")
        self.assertIsNone(create_body["data"].get("task_id"))
        self.mock_enqueue.assert_not_called()
        document_id = create_body["data"]["id"]

        list_response = self.client.get("/api/v1/documents/list?page=1&page_size=10&knowledge_base_id=1")
        self.assertEqual(list_response.status_code, 200)
        list_body = list_response.json()
        self.assertEqual(list_body["code"], 0)
        self.assertEqual(list_body["data"]["total"], 1)
        self.assertEqual(list_body["data"]["items"][0]["id"], document_id)

        detail_response = self.client.get(f"/api/v1/documents/detail?id={document_id}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["data"]["file_type"], "pdf")

        update_response = self.client.put(
            "/api/v1/documents/update",
            json={"id": document_id, "file_name": "renamed.pdf"},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["file_name"], "renamed.pdf")

        download_response = self.client.get(f"/api/v1/documents/download?id={document_id}")
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response.content, b"pdf-content")
        self.assertIn("renamed.pdf", download_response.headers["content-disposition"])

        delete_response = self.client.delete(f"/api/v1/documents/delete?id={document_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json(), {"code": 0, "message": "success", "data": None})
        self.assertEqual(self.fake_storage.objects, {})

    def test_create_document_requires_existing_knowledge_base(self):
        response = self.client.post(
            "/api/v1/documents/create",
            data={"knowledge_base_id": "999"},
            files={"file": ("missing.pdf", io.BytesIO(b"missing"), "application/pdf")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"code": 404, "message": "知识库不存在", "data": None})
        self.mock_enqueue.assert_not_called()

    def test_create_document_accepts_long_office_mime_type(self):
        """Office Open XML MIME 超过 50 字符，业务 file_type 应存为短扩展名。"""

        excel_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        self.assertGreater(len(excel_mime), 50)

        response = self.client.post(
            "/api/v1/documents/create",
            data={"knowledge_base_id": "1"},
            files={
                "file": (
                    "20260722134501-活跃用户弹窗.xlsx",
                    io.BytesIO(b"excel-content"),
                    excel_mime,
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["file_type"], "xlsx")
        self.assertEqual(body["data"]["file_name"], "20260722134501-活跃用户弹窗.xlsx")
        uploaded_object = next(iter(self.fake_storage.objects.values()))
        self.assertEqual(uploaded_object["content_type"], excel_mime)

    def test_list_document_chunks(self):
        create_response = self.client.post(
            "/api/v1/documents/create",
            data={"knowledge_base_id": "1"},
            files={"file": ("manual.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        document_id = create_response.json()["data"]["id"]

        db = self.SessionLocal()
        db.add(
            DocumentChunk(
                document_id=document_id,
                knowledge_base_id=1,
                chunk_index=0,
                content="hello chunk",
                content_hash="abc",
                page_number=None,
                token_count=11,
            )
        )
        db.commit()
        db.close()

        response = self.client.get(f"/api/v1/documents/chunks?document_id={document_id}&page=1&page_size=10")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["total"], 1)
        self.assertEqual(body["data"]["items"][0]["content"], "hello chunk")

    def test_manual_chunk_endpoint_enqueues_task(self):
        create_response = self.client.post(
            "/api/v1/documents/create",
            data={"knowledge_base_id": "1"},
            files={"file": ("manual.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        document_id = create_response.json()["data"]["id"]
        self.mock_enqueue.reset_mock()

        response = self.client.post("/api/v1/documents/chunk", json={"id": document_id})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["id"], document_id)
        self.assertEqual(body["data"]["task_id"], "fake-task-id")
        self.mock_enqueue.assert_called_once_with(document_id)

    def test_manual_chunk_rejects_processing_status(self):
        create_response = self.client.post(
            "/api/v1/documents/create",
            data={"knowledge_base_id": "1"},
            files={"file": ("busy.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        document_id = create_response.json()["data"]["id"]

        db = self.SessionLocal()
        document = db.query(Document).filter(Document.id == document_id).first()
        document.status = "parsing"
        db.commit()
        db.close()

        response = self.client.post("/api/v1/documents/chunk", json={"id": document_id})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 400)
        self.assertIn("正在处理中", body["message"])

    def test_manual_embed_endpoint_enqueues_task(self):
        """chunked 且有切片时，POST /embed 应投递向量化任务。"""
        create_response = self.client.post(
            "/api/v1/documents/create",
            data={"knowledge_base_id": "1"},
            files={"file": ("embed.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        document_id = create_response.json()["data"]["id"]

        db = self.SessionLocal()
        document = db.query(Document).filter(Document.id == document_id).first()
        document.status = "chunked"
        document.chunk_count = 2
        db.add(
            DocumentChunk(
                document_id=document_id,
                knowledge_base_id=1,
                chunk_index=0,
                content="chunk-a",
                content_hash="a" * 64,
                token_count=1,
            )
        )
        db.commit()
        db.close()

        self.mock_embed_enqueue.reset_mock()
        response = self.client.post("/api/v1/documents/embed", json={"id": document_id})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["id"], document_id)
        self.assertEqual(body["data"]["task_id"], "fake-embed-task-id")
        self.mock_embed_enqueue.assert_called_once_with(document_id)

    def test_manual_embed_rejects_uploaded_without_chunks(self):
        """未切片文档不可向量化。"""
        create_response = self.client.post(
            "/api/v1/documents/create",
            data={"knowledge_base_id": "1"},
            files={"file": ("nochunk.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        document_id = create_response.json()["data"]["id"]

        response = self.client.post("/api/v1/documents/embed", json={"id": document_id})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 400)
        self.assertIn("不可向量化", body["message"])


if __name__ == "__main__":
    unittest.main()
