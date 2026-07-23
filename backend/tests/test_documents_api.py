import io
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
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
        document_id = create_body["data"]["id"]

        list_response = self.client.get("/api/v1/documents/list?page=1&page_size=10&knowledge_base_id=1")
        self.assertEqual(list_response.status_code, 200)
        list_body = list_response.json()
        self.assertEqual(list_body["code"], 0)
        self.assertEqual(list_body["data"]["total"], 1)
        self.assertEqual(list_body["data"]["items"][0]["id"], document_id)

        detail_response = self.client.get(f"/api/v1/documents/detail?id={document_id}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["data"]["file_type"], "application/pdf")

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

    def test_create_document_accepts_long_office_mime_type(self):
        """Office Open XML MIME 超过 50 字符，应能正常入库。"""

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
        self.assertEqual(body["data"]["file_type"], excel_mime)
        self.assertEqual(body["data"]["file_name"], "20260722134501-活跃用户弹窗.xlsx")


if __name__ == "__main__":
    unittest.main()
