"""知识库管理接口测试。
测试使用 SQLite 内存库和 FastAPI 依赖覆盖，避免依赖 Neon 线上数据库。
"""

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User
from tests.auth_test_utils import auth_header_for_user, hashed_demo_password


class KnowledgeBaseApiTests(unittest.TestCase):
    def setUp(self):
        """准备测试数据库、测试用户和 TestClient。"""

        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        db = self.SessionLocal()
        db.add_all(
            [
                User(
                    id=101,
                    username="owner101",
                    email="owner101@example.com",
                    hashed_password=hashed_demo_password(),
                ),
                User(
                    id=202,
                    username="owner202",
                    email="owner202@example.com",
                    hashed_password=hashed_demo_password(),
                ),
            ]
        )
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
        self.headers_101 = auth_header_for_user(101, username="owner101")
        self.headers_202 = auth_header_for_user(202, username="owner202")

    def tearDown(self):
        """清理依赖覆盖和测试数据库表。"""

        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)

    def test_crud_uses_jwt_owner_and_unified_response(self):
        """验证知识库 CRUD 以 JWT 用户为 owner，并保持统一响应结构。"""

        primary_owner_id = 101
        secondary_owner_id = 202

        primary_create_response = self.client.post(
            "/api/v1/knowledge-bases/create",
            json={"name": "产品知识库", "description": "产品文档集合"},
            headers=self.headers_101,
        )
        secondary_create_response = self.client.post(
            "/api/v1/knowledge-bases/create",
            json={"name": "运营知识库", "description": "运营文档集合"},
            headers=self.headers_202,
        )

        self.assertEqual(primary_create_response.status_code, 200)
        self.assertEqual(secondary_create_response.status_code, 200)

        primary_create_body = primary_create_response.json()
        self.assertEqual(primary_create_body["code"], 0)
        self.assertEqual(primary_create_body["message"], "success")
        self.assertEqual(primary_create_body["data"]["name"], "产品知识库")
        self.assertEqual(primary_create_body["data"]["owner_id"], primary_owner_id)
        knowledge_base_id = primary_create_body["data"]["id"]

        primary_list_response = self.client.get(
            "/api/v1/knowledge-bases/list?page=1&page_size=10",
            headers=self.headers_101,
        )
        secondary_list_response = self.client.get(
            "/api/v1/knowledge-bases/list?page=1&page_size=10",
            headers=self.headers_202,
        )

        primary_list_body = primary_list_response.json()
        secondary_list_body = secondary_list_response.json()
        self.assertEqual(primary_list_body["code"], 0)
        self.assertEqual(primary_list_body["data"]["total"], 1)
        self.assertEqual(primary_list_body["data"]["page"], 1)
        self.assertEqual(primary_list_body["data"]["page_size"], 10)
        self.assertEqual(primary_list_body["data"]["items"][0]["id"], knowledge_base_id)
        self.assertEqual(primary_list_body["data"]["items"][0]["owner_id"], primary_owner_id)
        self.assertEqual(secondary_list_body["data"]["total"], 1)
        self.assertEqual(secondary_list_body["data"]["items"][0]["owner_id"], secondary_owner_id)

        detail_response = self.client.get(
            f"/api/v1/knowledge-bases/detail?id={knowledge_base_id}",
            headers=self.headers_101,
        )
        self.assertEqual(detail_response.json()["data"]["description"], "产品文档集合")

        update_response = self.client.put(
            "/api/v1/knowledge-bases/update",
            json={
                "id": knowledge_base_id,
                "name": "更新后的知识库",
                "description": "更新后的说明",
            },
            headers=self.headers_101,
        )
        update_body = update_response.json()
        self.assertEqual(update_body["code"], 0)
        self.assertEqual(update_body["data"]["name"], "更新后的知识库")

        delete_response = self.client.delete(
            f"/api/v1/knowledge-bases/delete?id={knowledge_base_id}",
            headers=self.headers_101,
        )
        self.assertEqual(delete_response.json(), {"code": 0, "message": "success", "data": None})

        missing_response = self.client.get(
            f"/api/v1/knowledge-bases/detail?id={knowledge_base_id}",
            headers=self.headers_101,
        )
        self.assertEqual(missing_response.status_code, 200)
        self.assertEqual(missing_response.json(), {"code": 404, "message": "知识库不存在", "data": None})

    def test_delete_rejects_knowledge_base_that_has_documents(self):
        """验证知识库存在关联文档时拒绝删除。"""

        from app.models.document import Document
        from app.models.knowledge_base import KnowledgeBase

        owner_id = 101

        db = self.SessionLocal()
        knowledge_base = KnowledgeBase(name="带文档知识库", description="不能直接删除", owner_id=owner_id)
        db.add(knowledge_base)
        db.commit()
        db.refresh(knowledge_base)
        db.add(
            Document(
                knowledge_base_id=knowledge_base.id,
                file_name="readme.pdf",
                file_type="pdf",
                file_path="/tmp/readme.pdf",
                file_size=100,
                status="uploaded",
            )
        )
        db.commit()
        knowledge_base_id = knowledge_base.id
        db.close()

        response = self.client.delete(
            f"/api/v1/knowledge-bases/delete?id={knowledge_base_id}",
            headers=self.headers_101,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"code": 400, "message": "知识库下存在文档，不能删除", "data": None},
        )


if __name__ == "__main__":
    unittest.main()
