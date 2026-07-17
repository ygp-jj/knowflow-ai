import unittest


class AppStartupTests(unittest.TestCase):
    def test_main_module_exposes_fastapi_app(self):
        from app.main import app

        self.assertIsNotNone(app)

    def test_settings_split_multiple_cors_origins(self):
        from app.core.config import Settings

        settings = Settings(
            database_url="sqlite://",
            redis_url="redis://localhost:6379/0",
            celery_broker_url="redis://localhost:6379/1",
            celery_result_backend="redis://localhost:6379/2",
            llm_base_url="https://example.com",
            llm_api_key="demo-key",
            embedding_base_url="https://example.com",
            embedding_api_key="demo-key",
            embedding_model="demo-embedding",
            cors_origins="http://localhost:5173, http://10.17.223.59:5173,https://admin.example.com",
        )

        self.assertEqual(
            settings.cors_origin_list,
            [
                "http://localhost:5173",
                "http://10.17.223.59:5173",
                "https://admin.example.com",
            ],
        )


if __name__ == "__main__":
    unittest.main()
