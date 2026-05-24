from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables."""
    from app.models import user, project, document, url_mapping, access_request, favorite  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Enable WAL mode for better concurrent performance
    async with engine.connect() as conn:
        await conn.execute(  # type: ignore
            __import__("sqlalchemy").text("PRAGMA journal_mode=WAL")
        )
        await conn.commit()

    # Migration: add allow_listing column if not exists
    async with engine.connect() as conn:
        result = await conn.execute(
            __import__("sqlalchemy").text("PRAGMA table_info(projects)")
        )
        columns = [row[1] for row in result.fetchall()]
        if "allow_listing" not in columns:
            await conn.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE projects ADD COLUMN allow_listing BOOLEAN NOT NULL DEFAULT 1"
                )
            )
            await conn.commit()

    # Migration: add description and is_deleted columns to documents
    async with engine.connect() as conn:
        result = await conn.execute(
            __import__("sqlalchemy").text("PRAGMA table_info(documents)")
        )
        columns = [row[1] for row in result.fetchall()]
        if "description" not in columns:
            await conn.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE documents ADD COLUMN description TEXT"
                )
            )
            await conn.commit()
        if "is_deleted" not in columns:
            await conn.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE documents ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0"
                )
            )
            await conn.commit()
        if "is_visible" not in columns:
            await conn.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE documents ADD COLUMN is_visible BOOLEAN NOT NULL DEFAULT 1"
                )
            )
            await conn.commit()
