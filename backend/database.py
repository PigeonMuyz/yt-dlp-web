"""
数据库连接和初始化
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from models import Base
from config import settings


engine = create_async_engine(settings.pg_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """获取数据库 session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """检查数据库连接"""
    try:
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        return True
    except Exception:
        return False
