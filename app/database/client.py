from config import TURSO_DB_URL, TURSO_AUTH_TOKEN
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


from .models import Base

engine = create_async_engine(
    TURSO_DB_URL, connect_args={"auth_token": TURSO_AUTH_TOKEN}
)
Session = async_sessionmaker(engine, expire_on_commit=False)


async def create_all():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
