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
            await conn.execute(text("ALTER TABLE app_settings ADD COLUMN scan_interval_seconds INTEGER DEFAULT 3"))
        except Exception:
            pass
            
        try:
            await conn.execute(text("ALTER TABLE app_settings ADD COLUMN purchase_interval_seconds INTEGER DEFAULT 1"))
        except Exception:
            pass

        try:
            await conn.execute(text("ALTER TABLE products ADD COLUMN post_purchase_action VARCHAR(20) DEFAULT 'pause'"))
        except Exception:
            pass

        # Migración: min_stock_to_trigger → min_local_to_trigger + min_transit_to_trigger
        try:
            await conn.execute(text("ALTER TABLE products ADD COLUMN min_local_to_trigger INTEGER DEFAULT 1"))
        except Exception:
            pass
        try:
            await conn.execute(text("ALTER TABLE products ADD COLUMN min_transit_to_trigger INTEGER DEFAULT 0"))
        except Exception:
            pass
            
        try:
            await conn.execute(text("ALTER TABLE products ADD COLUMN target_qty_local INTEGER DEFAULT 1"))
        except Exception:
            pass
            
        try:
            await conn.execute(text("ALTER TABLE products ADD COLUMN target_qty_transit INTEGER DEFAULT 0"))
        except Exception:
            pass
        # Copiar valor viejo de min_stock_to_trigger a min_local_to_trigger si existe
        try:
            await conn.execute(text("""
                UPDATE products 
                SET min_local_to_trigger = min_stock_to_trigger 
                WHERE min_stock_to_trigger IS NOT NULL 
                  AND min_local_to_trigger = 1
            """))
        except Exception:
            pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
