from sqlalchemy import text
from app.database import engine


SQL_COMMANDS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR DEFAULT 'free'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS monthly_generation_limit INTEGER DEFAULT 5",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",

    "UPDATE users SET plan = 'free' WHERE plan IS NULL OR plan = ''",
    "UPDATE users SET monthly_generation_limit = 5 WHERE monthly_generation_limit IS NULL",
    "UPDATE users SET is_active = TRUE WHERE is_active IS NULL",
    "UPDATE users SET is_admin = FALSE WHERE is_admin IS NULL",

    """
    CREATE TABLE IF NOT EXISTS usage_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        endpoint VARCHAR NOT NULL,
        project_name VARCHAR,
        status VARCHAR NOT NULL DEFAULT 'success',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


def main():
    print("Iniciando migração manual do PostgreSQL...")

    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")

    try:
        conn.execute(text("SET statement_timeout = '30000'"))

        for sql in SQL_COMMANDS:
            print("Executando:", sql.strip().split("\n")[0])
            conn.execute(text(sql))

        print("MIGRATIONS OK")

    finally:
        conn.close()


if __name__ == "__main__":
    main()