"""登录鉴权接口单测。"""

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.user import User
from tests.auth_test_utils import DEMO_PASSWORD, hashed_demo_password


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        db = self.SessionLocal()
        db.add(
            User(
                id=101,
                username="hr_admin",
                email="hr_admin@knowflow.ai",
                hashed_password=hashed_demo_password(),
            )
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

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)

    def test_login_success(self):
        """hr_admin / demo123456 可登录并拿到 token。"""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "hr_admin", "password": DEMO_PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertIn("access_token", body["data"])
        self.assertEqual(body["data"]["token_type"], "bearer")
        self.assertEqual(body["data"]["user"]["id"], 101)
        self.assertEqual(body["data"]["user"]["username"], "hr_admin")

    def test_login_failure(self):
        """错误密码返回业务 code=401。"""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "hr_admin", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 401)
        self.assertEqual(body["message"], "用户名或密码错误")
        self.assertIsNone(body["data"])

    def test_me_requires_bearer(self):
        """/me 无 Token 返回 HTTP 401。"""
        response = self.client.get("/api/v1/auth/me")
        self.assertEqual(response.status_code, 401)

    def test_me_with_valid_token(self):
        """带有效 Token 可获取当前用户。"""
        token = create_access_token(subject=101, extra_claims={"username": "hr_admin"})
        response = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["username"], "hr_admin")

    def test_knowledge_bases_list_requires_auth(self):
        """无 token 访问知识库列表返回 HTTP 401。"""
        response = self.client.get("/api/v1/knowledge-bases/list")
        self.assertEqual(response.status_code, 401)

    def test_register_success_auto_login(self):
        """注册成功后直接返回 token，可访问 /me。"""
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "username": "newbie",
                "email": "newbie@example.com",
                "password": "demo123456",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        token = body["data"]["access_token"]
        self.assertEqual(body["data"]["user"]["username"], "newbie")
        me = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me.json()["data"]["email"], "newbie@example.com")

    def test_register_duplicate_username(self):
        """重复用户名返回 code=400。"""
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "username": "hr_admin",
                "email": "another@example.com",
                "password": "demo123456",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 400)
        self.assertEqual(body["message"], "用户名已存在")

    def test_register_duplicate_email(self):
        """重复邮箱返回 code=400。"""
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "username": "other_user",
                "email": "hr_admin@knowflow.ai",
                "password": "demo123456",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 400)
        self.assertEqual(body["message"], "邮箱已存在")

    def test_register_chinese_username(self):
        """中文用户名可注册成功。"""
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "username": "聪明鸭",
                "email": "smart_duck@example.com",
                "password": "123456",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["user"]["username"], "聪明鸭")


if __name__ == "__main__":
    unittest.main()
