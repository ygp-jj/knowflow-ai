"""Chat 问答接口单测。"""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.schemas.chat import ChatAskRead


class ChatApiTests(unittest.TestCase):
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
        db.commit()
        db.close()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)

    def test_ask_validation_empty_question(self):
        response = self.client.post(
            "/api/v1/chat/ask",
            json={"knowledge_base_id": 1, "question": ""},
        )
        self.assertEqual(response.status_code, 422)

    @patch("app.api.v1.chat.ask_knowledge_base")
    def test_ask_success(self, mock_ask):
        mock_ask.return_value = ChatAskRead(
            answer="答案",
            question="问题",
            knowledge_base_id=1,
            references=[],
        )
        response = self.client.post(
            "/api/v1/chat/ask",
            json={"knowledge_base_id": 1, "question": "问题"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["answer"], "答案")

    @patch("app.api.v1.chat.ask_knowledge_base")
    def test_ask_kb_not_found(self, mock_ask):
        from app.services.rag_service import RagServiceError

        mock_ask.side_effect = RagServiceError("知识库不存在", http_code=404)
        response = self.client.post(
            "/api/v1/chat/ask",
            json={"knowledge_base_id": 9, "question": "问题"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 404)
        self.assertIsNone(body["data"])

    @patch("app.api.v1.chat.iter_ask_knowledge_base_events")
    def test_ask_stream_sse_shape(self, mock_iter):
        mock_iter.return_value = iter(
            [
                {"event": "references", "references": []},
                {"event": "token", "text": "你好"},
                {"event": "done", "ok": True},
            ]
        )
        response = self.client.post(
            "/api/v1/chat/ask-stream",
            json={"knowledge_base_id": 1, "question": "问题"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers.get("content-type", ""))
        body = response.text
        self.assertIn("event: references", body)
        self.assertIn("event: token", body)
        self.assertIn("event: done", body)
        self.assertIn("你好", body)


if __name__ == "__main__":
    unittest.main()
