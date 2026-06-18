import unittest


class AppStartupTests(unittest.TestCase):
    def test_main_module_exposes_fastapi_app(self):
        from app.main import app

        self.assertIsNotNone(app)


if __name__ == "__main__":
    unittest.main()
