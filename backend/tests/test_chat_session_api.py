"""会话 CRUD 与会话流式问答单测。"""

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.chat import ChatMessage, ChatSession
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.schemas.chat import ChatReference, DEFAULT_SESSION_TITLE
from app.services.rag_service import NO_HIT_ANSWER, iter_session_ask_events


class ChatSessionApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(self.engine, "connect")
        def _fk_on(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        db = self.SessionLocal()
        db.add(User(id=101, username="u", email="u@example.com", hashed_password="x"))
        db.commit()
        db.add(KnowledgeBase(id=201, name="请假库", description=None, owner_id=101))
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

    def test_session_crud_and_auto_title(self):
        create_resp = self.client.post(
            "/api/v1/chat/sessions/create",
            json={"user_id": 101, "knowledge_base_id": 201},
        )
        self.assertEqual(create_resp.status_code, 200)
        body = create_resp.json()
        self.assertEqual(body["code"], 0)
        session_id = body["data"]["id"]
        self.assertEqual(body["data"]["title"], DEFAULT_SESSION_TITLE)
        self.assertEqual(body["data"]["knowledge_base_name"], "请假库")

        list_resp = self.client.get(
            "/api/v1/chat/sessions/list",
            params={"user_id": 101, "page": 1, "page_size": 10},
        )
        self.assertEqual(list_resp.json()["data"]["total"], 1)

        rename = self.client.put(
            "/api/v1/chat/sessions/update",
            json={"id": session_id, "user_id": 101, "title": "我的请假会话"},
        )
        self.assertEqual(rename.json()["data"]["title"], "我的请假会话")

        delete_resp = self.client.delete(
            "/api/v1/chat/sessions/delete",
            params={"id": session_id, "user_id": 101},
        )
        self.assertEqual(delete_resp.json()["code"], 0)
        list_resp2 = self.client.get(
            "/api/v1/chat/sessions/list",
            params={"user_id": 101},
        )
        self.assertEqual(list_resp2.json()["data"]["total"], 0)

    @patch("app.services.rag_service.prepare_retrieval")
    @patch("app.services.rag_service.get_llm_service")
    def test_session_ask_stream_persists_user_and_assistant(self, mock_get_llm, mock_prepare):
        from app.services.rag_service import RetrievalBundle

        create_resp = self.client.post(
            "/api/v1/chat/sessions/create",
            json={"user_id": 101, "knowledge_base_id": 201},
        )
        session_id = create_resp.json()["data"]["id"]

        mock_prepare.return_value = RetrievalBundle(
            question="年假几天",
            knowledge_base_id=201,
            messages=None,
            references=[
                ChatReference(
                    chunk_id=1,
                    document_id=1,
                    chunk_index=0,
                    score=0.9,
                    content="年假 5 天",
                )
            ],
            no_hit_answer=None,
            context="年假 5 天",
        )
        llm = MagicMock()
        llm.chat_stream.return_value = iter(["答", "案"])
        mock_get_llm.return_value = llm

        # 写引用需要 documents/chunks FK；本测只验证消息落库，避免引用 FK——改为无引用
        mock_prepare.return_value = RetrievalBundle(
            question="年假几天",
            knowledge_base_id=201,
            messages=None,
            references=[],
            no_hit_answer=None,
            context="年假 5 天",
        )

        response = self.client.post(
            "/api/v1/chat/sessions/ask-stream",
            json={"session_id": session_id, "user_id": 101, "question": "年假几天"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("event: token", response.text)
        self.assertIn('"text": "答"', response.text)
        self.assertIn('"text": "案"', response.text)

        db = self.SessionLocal()
        messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.id).all()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[1].role, "assistant")
        self.assertEqual(messages[1].content, "答案")
        self.assertEqual(messages[1].token_count, 2)
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        self.assertEqual(session.title, "年假几天")
        db.close()

        msg_list = self.client.get(
            "/api/v1/chat/messages/list",
            params={"session_id": session_id, "user_id": 101},
        )
        self.assertEqual(msg_list.json()["data"]["total"], 2)

    @patch("app.services.rag_service.prepare_retrieval")
    def test_session_ask_no_hit_persists_assistant_tip(self, mock_prepare):
        from app.services.rag_service import RetrievalBundle

        create_resp = self.client.post(
            "/api/v1/chat/sessions/create",
            json={"user_id": 101, "knowledge_base_id": 201},
        )
        session_id = create_resp.json()["data"]["id"]
        mock_prepare.return_value = RetrievalBundle(
            question="无关问题xyz",
            knowledge_base_id=201,
            messages=None,
            references=[],
            no_hit_answer=NO_HIT_ANSWER,
            context=None,
        )
        response = self.client.post(
            "/api/v1/chat/sessions/ask-stream",
            json={"session_id": session_id, "user_id": 101, "question": "无关问题xyz"},
        )
        self.assertIn(NO_HIT_ANSWER[:8], response.text)
        db = self.SessionLocal()
        messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).all()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1].content, NO_HIT_ANSWER)
        db.close()

    def test_manual_title_not_overwritten_by_auto(self):
        """已手动改名后，提问不再覆盖 title。"""
        create_resp = self.client.post(
            "/api/v1/chat/sessions/create",
            json={"user_id": 101, "knowledge_base_id": 201},
        )
        session_id = create_resp.json()["data"]["id"]
        self.client.put(
            "/api/v1/chat/sessions/update",
            json={"id": session_id, "user_id": 101, "title": "固定标题"},
        )

        db = self.SessionLocal()
        with patch("app.services.rag_service.prepare_retrieval") as mock_prepare:
            from app.services.rag_service import RetrievalBundle

            mock_prepare.return_value = RetrievalBundle(
                question="问题A",
                knowledge_base_id=201,
                messages=None,
                references=[],
                no_hit_answer=NO_HIT_ANSWER,
                context=None,
            )
            list(
                iter_session_ask_events(
                    db,
                    session_id=session_id,
                    user_id=101,
                    question="问题A",
                )
            )
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        self.assertEqual(session.title, "固定标题")
        db.close()


if __name__ == "__main__":
    unittest.main()
