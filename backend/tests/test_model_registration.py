"""Regression tests for ORM model registration during application startup."""

import subprocess
import sys
import unittest
from pathlib import Path


class ModelRegistrationTests(unittest.TestCase):
    """Verify application startup registers foreign-key target tables."""

    def test_app_startup_registers_users_table(self):
        """Ensure string-based foreign keys can resolve the users table."""

        backend_dir = Path(__file__).resolve().parents[1]
        command = (
            "from app.main import app; "
            "from app.core.database import Base; "
            "assert 'users' in Base.metadata.tables, sorted(Base.metadata.tables.keys())"
        )

        result = subprocess.run(
            [sys.executable, "-c", command],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
