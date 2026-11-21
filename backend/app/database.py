"""Database engine, session factory and declarative base."""
from datetime import timezone

from sqlalchemy import DateTime, create_engine, event
from sqlalchemy.types import TypeDecorator
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for every SQLAlchemy entity."""


class UTCDateTime(TypeDecorator):
    """Stores naive UTC in the database, always returns timezone-aware UTC datetimes."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


def make_engine(database_url: str) -> Engine:
    """Create an engine. SQLite gets foreign keys switched on."""
    kwargs: dict = {"future": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url or database_url in ("sqlite://", "sqlite:///"):
            kwargs["poolclass"] = StaticPool
    engine = create_engine(database_url, **kwargs)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_sqlite_fk(dbapi_connection, _record):  # pragma: no cover
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=True, expire_on_commit=False, class_=Session)


def init_db(engine: Engine) -> None:
    """Create all tables (importing the models registers them on Base)."""
    from app import models  # noqa: F401  (import registers the mappings)

    Base.metadata.create_all(bind=engine)
    _add_missing_nullable_columns(engine)


def _add_missing_nullable_columns(engine: Engine) -> None:
    """Tiny additive migration: databases created by an older version get any new nullable
    columns added automatically, so an existing itsm.db keeps working after an upgrade."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name not in existing and column.nullable and not column.foreign_keys:
                    ddl = column.type.compile(dialect=engine.dialect)
                    conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {ddl}'))


_default_engine: Engine | None = None
_default_factory: sessionmaker[Session] | None = None


def get_default_engine() -> Engine:
    global _default_engine
    if _default_engine is None:
        _default_engine = make_engine(get_settings().database_url)
    return _default_engine


def get_default_session_factory() -> sessionmaker[Session]:
    global _default_factory
    if _default_factory is None:
        _default_factory = make_session_factory(get_default_engine())
    return _default_factory
