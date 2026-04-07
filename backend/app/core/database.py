from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migración automática si la columna nueva no existe en la BD de Producción
        try:
            await conn.execute(text("ALTER TABLE app_settings ADD COLUMN scan_interval_seconds INTEGER DEFAULT 10"))
        except Exception:
            pass
        
        try:
            await conn.execute(text("ALTER TABLE products ADD COLUMN post_purchase_action VARCHAR(20) DEFAULT 'pause'"))
        except Exception:
            pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
