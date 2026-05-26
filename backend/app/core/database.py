from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


connect_args = {"check_same_thread": False, "timeout": 30} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)


@event.listens_for(engine, "connect")
def _configure_sqlite(connection, _record) -> None:  # type: ignore[no-untyped-def]
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
    finally:
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app.models import rfp  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_rfp_columns()
    _ensure_sqlite_embedding_columns()
    _ensure_sqlite_generation_columns()
    _ensure_sqlite_usage_tables()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_sqlite_embedding_columns() -> None:
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    required_columns = {
        "embedding_json": "TEXT",
        "embedding_model": "VARCHAR",
        "embedding_status": "VARCHAR DEFAULT 'pending'",
    }
    with engine.begin() as connection:
        existing = {row[1] for row in connection.execute(text("PRAGMA table_info(rfp_chunks)"))}
        for column_name, column_type in required_columns.items():
            if column_name not in existing:
                connection.execute(text(f"ALTER TABLE rfp_chunks ADD COLUMN {column_name} {column_type}"))


def _ensure_sqlite_rfp_columns() -> None:
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    required_columns = {
        "probable_title": "VARCHAR",
        "probable_client": "VARCHAR",
        "probable_deadline": "VARCHAR",
        "probable_submission_date": "VARCHAR",
    }
    with engine.begin() as connection:
        existing = {row[1] for row in connection.execute(text("PRAGMA table_info(rfp_documents)"))}
        for column_name, column_type in required_columns.items():
            if column_name not in existing:
                connection.execute(text(f"ALTER TABLE rfp_documents ADD COLUMN {column_name} {column_type}"))


def _ensure_sqlite_generation_columns() -> None:
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    required_columns = {
        "model_used": "VARCHAR",
        "average_seconds_per_section": "FLOAT",
        "estimated_total_seconds": "FLOAT",
        "estimated_remaining_seconds": "FLOAT",
        "elapsed_seconds": "FLOAT",
    }
    with engine.begin() as connection:
        existing = {row[1] for row in connection.execute(text("PRAGMA table_info(generation_jobs)"))}
        for column_name, column_type in required_columns.items():
            if column_name not in existing:
                connection.execute(text(f"ALTER TABLE generation_jobs ADD COLUMN {column_name} {column_type}"))


def _ensure_sqlite_usage_tables() -> None:
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS local_usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rfp_id INTEGER NULL,
                    operation_type VARCHAR NOT NULL,
                    model_used VARCHAR NULL,
                    prompt_word_count INTEGER NOT NULL DEFAULT 0,
                    response_word_count INTEGER NOT NULL DEFAULT 0,
                    estimated_prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    estimated_response_tokens INTEGER NOT NULL DEFAULT 0,
                    estimated_total_tokens INTEGER NOT NULL DEFAULT 0,
                    elapsed_seconds FLOAT NULL,
                    retrieval_chunks_used INTEGER NOT NULL DEFAULT 0,
                    external_api_used BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
