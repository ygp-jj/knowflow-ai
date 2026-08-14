"""文档向量化任务单测（Mock Embedding / Milvus，不连真实服务）。"""

import unittest
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.services.embedding_service import EmbeddingService, EmbeddingServiceError
from app.tasks.embedding_tasks import run_embed_document


class EmbeddingServiceUnitTests(unittest.TestCase):
    def test_embed_texts_batches_and_checks_dimension(self):
        """应按 batch_size 分批，并校验返回维度。"""
        client = MagicMock()
        first = MagicMock()
        first.data = [
            MagicMock(index=0, embedding=[0.1, 0.2]),
            MagicMock(index=1, embedding=[0.3, 0.4]),
        ]
        second = MagicMock()
        second.data = [MagicMock(index=0, embedding=[0.5, 0.6])]
        client.embeddings.create.side_effect = [first, second]

        service = EmbeddingService(client=client, model="demo", dimension=2, batch_size=2)
        vectors = service.embed_texts(["a", "b", "c"])

        self.assertEqual(len(vectors), 3)
        self.assertEqual(client.embeddings.create.call_count, 2)
        self.assertEqual(vectors[2], [0.5, 0.6])

    def test_embed_texts_rejects_wrong_dimension(self):
        client = MagicMock()
        response = MagicMock()
        response.data = [MagicMock(index=0, embedding=[1.0, 2.0, 3.0])]
        client.embeddings.create.return_value = response

        service = EmbeddingService(client=client, model="demo", dimension=2, batch_size=8)
        with self.assertRaises(EmbeddingServiceError) as ctx:
            service.embed_texts(["hello"])
        self.assertIn("维度不匹配", str(ctx.exception))


class EmbedDocumentTaskTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        import app.core.database as database
        import app.tasks.embedding_tasks as embedding_tasks

        self._original_session_local = database.SessionLocal
        database.SessionLocal = self.SessionLocal
        embedding_tasks.SessionLocal = self.SessionLocal

        db = self.SessionLocal()
        db.add(User(id=1, username="u", email="u@example.com", hashed_password="x"))
        db.add(KnowledgeBase(id=1, name="kb", description=None, owner_id=1))
        document = Document(
            knowledge_base_id=1,
            file_name="demo.txt",
            file_type="txt",
            file_path="knowledge-bases/1/demo.txt",
            file_size=10,
            status="chunked",
            chunk_count=2,
        )
        db.add(document)
        db.flush()
        db.add_all(
            [
                DocumentChunk(
                    document_id=document.id,
                    knowledge_base_id=1,
                    chunk_index=0,
                    content="父块标题",
                    content_hash="a" * 64,
                    token_count=2,
                ),
                DocumentChunk(
                    document_id=document.id,
                    knowledge_base_id=1,
                    chunk_index=1,
                    content="子块正文",
                    content_hash="b" * 64,
                    token_count=3,
                ),
            ]
        )
        db.commit()
        db.refresh(document)
        self.document_id = document.id
        db.close()

    def tearDown(self):
        import app.core.database as database
        import app.tasks.embedding_tasks as embedding_tasks

        database.SessionLocal = self._original_session_local
        embedding_tasks.SessionLocal = self._original_session_local
        Base.metadata.drop_all(bind=self.engine)

    def test_run_embed_document_success_to_embedded(self):
        """Mock Embedding/Milvus 后应写入 vector_id 并将状态置为 embedded。"""
        embedding_service = MagicMock()
        embedding_service.embed_texts.return_value = [[0.1, 0.2], [0.3, 0.4]]

        milvus_service = MagicMock()

        # 让 upsert 返回与真实 chunk.id 对齐的 vector_id，便于断言回填
        def _upsert(rows):
            return [str(row["chunk_id"]) for row in rows]

        milvus_service.upsert_chunk_embeddings.side_effect = _upsert

        result = run_embed_document(
            self.document_id,
            embedding_service=embedding_service,
            milvus_service=milvus_service,
        )

        self.assertEqual(result["status"], "embedded")
        self.assertEqual(result["embedded_count"], 2)
        milvus_service.delete_by_document_id.assert_called_once_with(self.document_id)
        milvus_service.upsert_chunk_embeddings.assert_called_once()

        db = self.SessionLocal()
        document = db.query(Document).filter(Document.id == self.document_id).first()
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == self.document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        self.assertEqual(document.status, "embedded")
        self.assertIsNone(document.error_message)
        self.assertEqual(chunks[0].vector_id, str(chunks[0].id))
        self.assertEqual(chunks[1].vector_id, str(chunks[1].id))
        db.close()

    def test_run_embed_document_embedding_failure_marks_failed(self):
        embedding_service = MagicMock()
        embedding_service.embed_texts.side_effect = EmbeddingServiceError("上游超时")
        milvus_service = MagicMock()

        result = run_embed_document(
            self.document_id,
            embedding_service=embedding_service,
            milvus_service=milvus_service,
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn("上游超时", result["error"])
        milvus_service.upsert_chunk_embeddings.assert_not_called()

        db = self.SessionLocal()
        document = db.query(Document).filter(Document.id == self.document_id).first()
        self.assertEqual(document.status, "failed")
        self.assertIn("上游超时", document.error_message or "")
        db.close()


if __name__ == "__main__":
    unittest.main()
