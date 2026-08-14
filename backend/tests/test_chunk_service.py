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
from app.services.chunk_service import (
    expand_chunks_for_retrieval,
    list_child_chunks,
    list_chunks,
    replace_document_chunks,
)


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

    def test_replace_resolves_parent_chunk_id_and_expand(self):
        """写入后应将 parent_chunk_index 解析为 parent_chunk_id，并支持命中父块扩子块。"""

        payload = [
            {
                "content": "第四章 请假流程",
                "page_number": None,
                "chunk_index": 0,
                "parent_chunk_index": None,
                "metadata": {"boundary_type": "title", "section_level": 1},
            },
            {
                "content": "第十五条 请假流程",
                "page_number": None,
                "chunk_index": 1,
                "parent_chunk_index": 0,
                "metadata": {"boundary_type": "title", "section_level": 2},
            },
            {
                "content": "1. 申请：提前填写申请单",
                "page_number": None,
                "chunk_index": 2,
                "parent_chunk_index": 1,
                "metadata": {"boundary_type": "title_with_body", "section_level": 3},
            },
            {
                "content": "2. 审批：24小时内批复",
                "page_number": None,
                "chunk_index": 3,
                "parent_chunk_index": 1,
                "metadata": {"boundary_type": "title_with_body", "section_level": 3},
            },
        ]
        created = replace_document_chunks(self.db, self.document, payload)
        self.assertEqual(len(created), 4)
        self.assertIsNone(created[0].parent_chunk_id)
        self.assertEqual(created[1].parent_chunk_id, created[0].id)
        self.assertEqual(created[2].parent_chunk_id, created[1].id)
        self.assertEqual(created[3].parent_chunk_id, created[1].id)

        children, total = list_chunks(
            self.db, self.document.id, page=1, page_size=10, parent_id=created[1].id,
        )
        self.assertEqual(total, 2)
        self.assertEqual([item.content for item in children], [
            "1. 申请：提前填写申请单",
            "2. 审批：24小时内批复",
        ])

        expanded = expand_chunks_for_retrieval(self.db, [created[0]], max_depth=2)
        self.assertEqual(
            [item.content for item in expanded],
            [
                "第四章 请假流程",
                "第十五条 请假流程",
                "1. 申请：提前填写申请单",
                "2. 审批：24小时内批复",
            ],
        )
        self.assertEqual(len(list_child_chunks(self.db, created[0].id)), 1)


if __name__ == "__main__":
    unittest.main()
