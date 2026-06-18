import unittest
from pathlib import Path
from uuid import uuid4

import psycopg


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_ENV_PATH = ROOT_DIR / "backend" / ".env"
SQL_FILE_PATH = ROOT_DIR / "backend" / "scripts" / "neon-create-knowflow-tables.sql"


def load_database_url() -> str:
    for line in BACKEND_ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("DATABASE_URL not found in backend/.env")


class NeonBootstrapSqlTests(unittest.TestCase):
    def test_sql_script_creates_expected_tables_and_enums(self):
        self.assertTrue(SQL_FILE_PATH.exists(), f"Missing SQL file: {SQL_FILE_PATH}")

        expected_tables = {
            "users",
            "knowledge_bases",
            "documents",
            "document_chunks",
            "chat_sessions",
            "chat_messages",
            "chat_references",
            "prompt_templates",
            "model_configs",
            "question_feedbacks",
            "evaluation_cases",
            "evaluation_runs",
        }

        expected_enums = {
            "document_status_enum": [
                "uploaded",
                "parsing",
                "chunking",
                "embedding",
                "indexed",
                "failed",
            ],
            "chat_role_enum": ["user", "assistant", "system"],
            "model_type_enum": ["chat", "embedding", "rerank"],
            "feedback_rating_enum": ["like", "dislike"],
        }

        schema_name = f"test_bootstrap_{uuid4().hex[:8]}"
        sql_script = SQL_FILE_PATH.read_text(encoding="utf-8")

        with psycopg.connect(load_database_url(), autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(f'CREATE SCHEMA "{schema_name}"')
                try:
                    cur.execute(f'SET search_path TO "{schema_name}"')
                    cur.execute(sql_script)

                    cur.execute(
                        """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = %s
                        ORDER BY table_name
                        """,
                        (schema_name,),
                    )
                    actual_tables = {row[0] for row in cur.fetchall()}
                    self.assertTrue(expected_tables.issubset(actual_tables))

                    cur.execute(
                        """
                        SELECT t.typname, e.enumlabel
                        FROM pg_type t
                        JOIN pg_enum e ON e.enumtypid = t.oid
                        JOIN pg_namespace n ON n.oid = t.typnamespace
                        WHERE n.nspname = %s
                        ORDER BY t.typname, e.enumsortorder
                        """,
                        (schema_name,),
                    )
                    actual_enum_rows = cur.fetchall()
                    actual_enums = {}
                    for enum_name, enum_label in actual_enum_rows:
                        actual_enums.setdefault(enum_name, []).append(enum_label)

                    self.assertEqual(actual_enums, expected_enums)
                finally:
                    cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')


if __name__ == "__main__":
    unittest.main()
