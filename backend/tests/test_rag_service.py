"""RAG 编排服务单测（Mock Embedding / Milvus / LLM）。"""

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
from app.services.rag_service import NO_HIT_ANSWER, RagServiceError, ask_knowledge_base


class RagServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        db = self.SessionLocal()
        db.add(User(id=1, username="u", email="u@example.com", hashed_password="x"))
        db.add(KnowledgeBase(id=1, name="kb", description=None, owner_id=1))
        doc = Document(
            knowledge_base_id=1,
            file_name="a.txt",
            file_type="txt",
            file_path="p",
            file_size=1,
            status="embedded",
            chunk_count=2,
        )
        db.add(doc)
        db.flush()
        self.doc_id = doc.id
        parent = DocumentChunk(
            document_id=doc.id,
            knowledge_base_id=1,
            chunk_index=0,
            content="请假制度",
            content_hash="a" * 64,
            token_count=2,
        )
        db.add(parent)
        db.flush()
        child = DocumentChunk(
            document_id=doc.id,
            knowledge_base_id=1,
            parent_chunk_id=parent.id,
            chunk_index=1,
            content="直属主管审批",
            content_hash="b" * 64,
            token_count=3,
        )
        db.add(child)
        db.commit()
        self.parent_id = parent.id
        self.child_id = child.id
        db.close()

    def tearDown(self):
        Base.metadata.drop_all(bind=self.engine)

    def test_kb_not_found(self):
        db = self.SessionLocal()
        with self.assertRaises(RagServiceError) as ctx:
            ask_knowledge_base(
                db,
                knowledge_base_id=999,
                question="请假找谁",
                embedding_service=MagicMock(),
                milvus_service=MagicMock(),
                llm_service=MagicMock(),
            )
        self.assertEqual(ctx.exception.http_code, 404)
        db.close()

    def test_no_hit_returns_friendly_answer(self):
        db = self.SessionLocal()
        embedder = MagicMock()
        embedder.embed_query.return_value = [0.1, 0.2]
        milvus = MagicMock()
        milvus.search.return_value = []
        llm = MagicMock()

        result = ask_knowledge_base(
            db,
            knowledge_base_id=1,
            question="完全无关的问题",
            embedding_service=embedder,
            milvus_service=milvus,
            llm_service=llm,
            score_threshold=0.3,
        )
        self.assertEqual(result.answer, NO_HIT_ANSWER)
        self.assertEqual(result.references, [])
        llm.chat.assert_not_called()
        db.close()

    def test_hit_calls_llm_and_returns_references(self):
        db = self.SessionLocal()
        embedder = MagicMock()
        embedder.embed_query.return_value = [0.1] * 8
        milvus = MagicMock()
        milvus.search.return_value = [
            {
                "chunk_id": self.parent_id,
                "document_id": self.doc_id,
                "chunk_index": 0,
                "content": "请假制度",
                "score": 0.9,
            }
        ]
        llm = MagicMock()
        llm.chat.return_value = "需要直属主管审批。"

        result = ask_knowledge_base(
            db,
            knowledge_base_id=1,
            question="请假找谁审批",
            embedding_service=embedder,
            milvus_service=milvus,
            llm_service=llm,
            score_threshold=0.3,
        )
        self.assertIn("直属主管", result.answer)
        self.assertEqual(len(result.references), 1)
        self.assertEqual(result.references[0].chunk_id, self.parent_id)
        self.assertEqual(result.references[0].score, 0.9)
        llm.chat.assert_called_once()
        # 上下文应包含扩出的子块
        user_msg = llm.chat.call_args[0][0][1]["content"]
        self.assertIn("直属主管审批", user_msg)
        db.close()

    def test_stream_events_order(self):
        """流式应先 references，再 token，最后 done。"""
        from app.services.rag_service import iter_ask_knowledge_base_events

        db = self.SessionLocal()
        embedder = MagicMock()
        embedder.embed_query.return_value = [0.1] * 8
        milvus = MagicMock()
        milvus.search.return_value = [
            {
                "chunk_id": self.parent_id,
                "document_id": self.doc_id,
                "chunk_index": 0,
                "content": "请假制度",
                "score": 0.9,
            }
        ]
        llm = MagicMock()
        llm.chat_stream.return_value = iter(["答", "案"])

        events = list(
            iter_ask_knowledge_base_events(
                db,
                knowledge_base_id=1,
                question="请假找谁",
                embedding_service=embedder,
                milvus_service=milvus,
                llm_service=llm,
                score_threshold=0.3,
            )
        )
        self.assertEqual(events[0]["event"], "references")
        self.assertEqual(events[1], {"event": "token", "text": "答"})
        self.assertEqual(events[2], {"event": "token", "text": "案"})
        self.assertEqual(events[-1], {"event": "done", "ok": True})
        db.close()


if __name__ == "__main__":
    unittest.main()
