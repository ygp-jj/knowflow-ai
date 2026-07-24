"""切片写入服务单测。"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.services.chunk_service import list_chunks, replace_document_chunks


class ChunkServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        self.db = self.SessionLocal()
        self.db.add(User(id=1, username="u", email="u@example.com", hashed_password="x"))
        self.db.add(KnowledgeBase(id=1, name="kb", description=None, owner_id=1))
        self.document = Document(
            knowledge_base_id=1,
            file_name="a.txt",
            file_type="txt",
            file_path="knowledge-bases/1/a.txt",
            file_size=10,
            status="chunking",
            chunk_count=0,
        )
        self.db.add(self.document)
        self.db.commit()
        self.db.refresh(self.document)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_replace_document_chunks_is_idempotent(self):
        first = [
            {"content": "chunk-1", "page_number": None, "chunk_index": 0},
            {"content": "chunk-2", "page_number": None, "chunk_index": 1},
        ]
        replace_document_chunks(self.db, self.document, first)
        self.assertEqual(self.document.chunk_count, 2)

        second = [{"content": "only-one", "page_number": 1, "chunk_index": 0}]
        replace_document_chunks(self.db, self.document, second)

        items, total = list_chunks(self.db, self.document.id, page=1, page_size=10)
        self.assertEqual(total, 1)
        self.assertEqual(self.document.chunk_count, 1)
        self.assertEqual(items[0].content, "only-one")
        self.assertEqual(self.db.query(DocumentChunk).count(), 1)


if __name__ == "__main__":
    unittest.main()
