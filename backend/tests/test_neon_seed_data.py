import unittest
from pathlib import Path
from uuid import uuid4

import psycopg


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_ENV_PATH = ROOT_DIR / "backend" / ".env"
BOOTSTRAP_SQL_FILE_PATH = ROOT_DIR / "backend" / "scripts" / "neon-create-knowflow-tables.sql"
SEED_SQL_FILE_PATH = ROOT_DIR / "backend" / "scripts" / "neon-seed-knowflow-data.sql"


def load_database_url() -> str:
    for line in BACKEND_ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("DATABASE_URL not found in backend/.env")


class NeonSeedDataTests(unittest.TestCase):
    def test_seed_sql_single_demo_user_and_expected_counts(self):
        """单演示账号 seed：users=1，业务演示表各 2 条，prompt/model 仍 4 条。"""
        self.assertTrue(SEED_SQL_FILE_PATH.exists(), f"Missing seed SQL file: {SEED_SQL_FILE_PATH}")
        self.assertTrue(BOOTSTRAP_SQL_FILE_PATH.exists(), f"Missing bootstrap SQL file: {BOOTSTRAP_SQL_FILE_PATH}")

        expected_counts = {
            "users": 1,
            "knowledge_bases": 2,
            "documents": 2,
            "document_chunks": 2,
            "chat_sessions": 2,
            "chat_messages": 2,
            "chat_references": 2,
            "prompt_templates": 4,
            "model_configs": 4,
            "question_feedbacks": 2,
            "evaluation_cases": 2,
            "evaluation_runs": 2,
        }

        schema_name = f"test_seed_{uuid4().hex[:8]}"
        bootstrap_sql = BOOTSTRAP_SQL_FILE_PATH.read_text(encoding="utf-8")
        seed_sql = SEED_SQL_FILE_PATH.read_text(encoding="utf-8")

        with psycopg.connect(load_database_url(), autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(f'CREATE SCHEMA "{schema_name}"')
                try:
                    cur.execute(f'SET search_path TO "{schema_name}"')
                    cur.execute(bootstrap_sql)
                    cur.execute(seed_sql)

                    for table_name, expected in expected_counts.items():
                        cur.execute(f'SELECT COUNT(*) FROM "{schema_name}".{table_name}')
                        row_count = cur.fetchone()[0]
                        self.assertEqual(row_count, expected, table_name)

                    cur.execute(f'SELECT username FROM "{schema_name}".users')
                    self.assertEqual(cur.fetchone()[0], "hr_admin")

                    cur.execute(
                        f"""
                        SELECT COUNT(*)
                        FROM "{schema_name}".question_feedbacks qf
                        JOIN "{schema_name}".chat_messages cm ON cm.id = qf.message_id
                        WHERE cm.role = 'assistant'
                        """
                    )
                    self.assertEqual(cur.fetchone()[0], 2)
                finally:
                    cur.execute("RESET search_path")
                    cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')


if __name__ == "__main__":
    unittest.main()
