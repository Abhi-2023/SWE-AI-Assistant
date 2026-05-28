from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

async_engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=False)
async_session = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    db = async_session()
    try:
        yield db
    except Exception as e:
        await db.rollback()
        raise
    finally:
        await db.close()
        
async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        