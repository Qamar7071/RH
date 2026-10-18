"""Database layer: project requests (leads) and chatbot conversations.

Works with SQLite (local) and PostgreSQL (production) through SQLAlchemy.
"""
from datetime import datetime, timezone

from sqlalchemy import (Column, DateTime, Integer, MetaData, String, Table, Text,
                        create_engine, func, insert, select)

metadata = MetaData()

LEAD_FIELDS = ("name", "email", "company", "service", "budget", "deadline", "details", "ip", "user_agent")

leads = Table(
    "leads", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("name", String(100), nullable=False),
    Column("email", String(200), nullable=False),
    Column("company", String(150), nullable=False, default=""),
    Column("service", String(60), nullable=False),
    Column("budget", String(60), nullable=False, default=""),
    Column("deadline", String(60), nullable=False, default=""),
    Column("details", Text, nullable=False),
    Column("ip", String(64), nullable=False, default=""),
    Column("user_agent", String(300), nullable=False, default=""),
    Column("status", String(20), nullable=False, default="new"),
)

chat_logs = Table(
    "chat_logs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("session_id", String(64), nullable=False),
    Column("question", Text, nullable=False),
    Column("answer", Text, nullable=False),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_url(url: str) -> str:
    """Accept postgres:// and postgresql:// URLs and use the psycopg 3 driver."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class Storage:
    def __init__(self, url: str) -> None:
        url = normalize_url(url)
        kwargs = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            kwargs.update(pool_size=5, max_overflow=5, pool_recycle=280)
        self.engine = create_engine(url, **kwargs)
        metadata.create_all(self.engine)

    # ---- leads ----
    def add_lead(self, lead: dict) -> int:
        values = {k: str(lead.get(k, "") or "") for k in LEAD_FIELDS}
        with self.engine.begin() as conn:
            result = conn.execute(insert(leads).values(created_at=_now(), status="new", **values))
            return int(result.inserted_primary_key[0])

    def list_leads(self, limit: int = 200) -> list:
        with self.engine.connect() as conn:
            rows = conn.execute(select(leads).order_by(leads.c.id.desc()).limit(limit)).mappings()
            return [dict(r) for r in rows]

    def count_leads(self) -> int:
        with self.engine.connect() as conn:
            return int(conn.execute(select(func.count()).select_from(leads)).scalar_one())

    # ---- chat ----
    def log_chat(self, session_id: str, question: str, answer: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(insert(chat_logs).values(
                created_at=_now(), session_id=session_id[:64], question=question[:2000], answer=answer[:4000]))

    def recent_chats(self, limit: int = 100) -> list:
        with self.engine.connect() as conn:
            rows = conn.execute(select(chat_logs).order_by(chat_logs.c.id.desc()).limit(limit)).mappings()
            return [dict(r) for r in rows]

    def ping(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(select(1))
            return True
        except Exception:
            return False
