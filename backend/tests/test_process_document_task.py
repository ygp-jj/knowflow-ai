"""文档解析切片任务单测。"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.chunk import DocumentChunk  # noqa: F401
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.tasks.document_tasks import run_process_document


class FakeObjectStorage:
    """内存对象存储。"""

    def __init__(self):
        self.objects = {}

    def upload_file(self, file_bytes: bytes, object_name: str, content_type: str):
        self.objects[object_name] = {"bytes": file_bytes, "content_type": content_type}
        return object_name

    def download_file(self, object_name: str):
        return self.objects.get(object_name)

    def delete_file(self, object_name: str):
        self.objects.pop(object_name, None)


class ProcessDocumentTaskTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        # 将任务使用的 SessionLocal 替换为测试库。
        import app.tasks.document_tasks as document_tasks
        import app.core.database as database

        self._original_session_local = database.SessionLocal
        database.SessionLocal = self.SessionLocal
        document_tasks.SessionLocal = self.SessionLocal

        db = self.SessionLocal()
        db.add(User(id=1, username="u", email="u@example.com", hashed_password="x"))
        db.add(KnowledgeBase(id=1, name="kb", description=None, owner_id=1))
        self.storage = FakeObjectStorage()
        object_name = "knowledge-bases/1/demo.txt"
        self.storage.upload_file(("员工手册内容足够用于切片测试。" * 5).encode("utf-8"), object_name, "text/plain")
        document = Document(
            knowledge_base_id=1,
            file_name="demo.txt",
            file_type="txt",
            file_path=object_name,
            file_size=100,
            status="uploaded",
            chunk_count=0,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        self.document_id = document.id
        db.close()

    def tearDown(self):
        import app.tasks.document_tasks as document_tasks
        import app.core.database as database

        database.SessionLocal = self._original_session_local
        document_tasks.SessionLocal = self._original_session_local
        Base.metadata.drop_all(bind=self.engine)

    def test_run_process_document_success_to_chunked(self):
        result = run_process_document(self.document_id, object_storage=self.storage)

        self.assertEqual(result["status"], "chunked")
        self.assertGreater(result["chunk_count"], 0)

        db = self.SessionLocal()
        document = db.query(Document).filter(Document.id == self.document_id).first()
        self.assertEqual(document.status, "chunked")
        self.assertEqual(document.chunk_count, result["chunk_count"])
        self.assertEqual(db.query(DocumentChunk).filter(DocumentChunk.document_id == self.document_id).count(), result["chunk_count"])
        db.close()

    def test_run_process_document_unsupported_type_failed(self):
        db = self.SessionLocal()
        object_name = "knowledge-bases/1/demo.xlsx"
        self.storage.upload_file(b"excel", object_name, "application/octet-stream")
        document = Document(
            knowledge_base_id=1,
            file_name="demo.xlsx",
            file_type="xlsx",
            file_path=object_name,
            file_size=5,
            status="uploaded",
            chunk_count=0,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        document_id = document.id
        db.close()

        result = run_process_document(document_id, object_storage=self.storage)
        self.assertEqual(result["status"], "failed")

        db = self.SessionLocal()
        document = db.query(Document).filter(Document.id == document_id).first()
        self.assertEqual(document.status, "failed")
        self.assertIn("暂不支持", document.error_message or "")
        db.close()


if __name__ == "__main__":
    unittest.main()
