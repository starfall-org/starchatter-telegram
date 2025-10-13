import asyncio
from datetime import datetime, timedelta

from config import TURSO_AUTH_TOKEN, TURSO_DB_URL
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from typing_extensions import Self

from .models import Base, ChatSession, LLMConfig, LLMProvider, User


class Database:
    _timeout = timedelta(minutes=5)
    Session: async_sessionmaker

    def __new__(cls) -> Self:
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._last_used = datetime.now()
        self._disposed = False
        self._create_engine()
        self.Session = self._wrap_session()
        self._closing_task = asyncio.create_task(self._auto_close())
        self._initialized = True

    def _create_engine(self):
        self._engine = create_async_engine(
            TURSO_DB_URL, connect_args={"auth_token": TURSO_AUTH_TOKEN}
        )
        self._disposed = False

    def _wrap_session(self):
        """Trả về async_sessionmaker tự động reset timer và tái tạo engine nếu cần"""
        parent = self

        class AutoSession(async_sessionmaker):
            def __call__(self, *args, **kwargs) -> AsyncSession:
                parent._last_used = datetime.now()
                if parent._disposed:
                    parent._create_engine()
                    self.bind = parent._engine
                return super().__call__(*args, **kwargs)

        return AutoSession(self._engine, expire_on_commit=False)

    @property
    def engine(self):
        if self._disposed:
            self._create_engine()
        return self._engine

    async def create_all(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _auto_close(self):
        await self.create_all()
        while True:
            await asyncio.sleep(60)
            if datetime.now() - self._last_used > self._timeout:
                await self.engine.dispose()
                self._disposed = True
                break

    async def edit_llm_config(
        self,
        model: str | None = None,
        instructions: str | None = None,
        provider_id: int | None = None,
    ):
        async with self.Session() as session:
            result = await session.execute(
                select(LLMConfig).where(LLMConfig.model == model)
            )
            llm_config = result.scalars().first()
            if llm_config:
                if model:
                    llm_config.model = model
                if instructions:
                    llm_config.instructions = instructions
                if provider_id:
                    llm_config.provider_id = provider_id
                await session.commit()
            else:
                llm_config = LLMConfig(
                    model=model,
                    instructions=instructions,
                    provider_id=provider_id,
                )
                session.add(llm_config)
                await session.commit()

    async def add_provider(self, provider):
        async with self.Session() as session:
            session.add(provider)
            await session.commit()

    async def get_provider(self, provider_id):
        async with self.Session() as session:
            result = await session.execute(
                select(LLMProvider).where(LLMProvider.id == provider_id)
            )
            return result.scalars().first()

    async def update_provider(self, provider):
        async with self.Session() as session:
            session.merge(provider)
            await session.commit()

    async def get_providers(self):
        async with self.Session() as session:
            result = await session.execute(select(LLMProvider))
            return result.scalars().all()

    async def get_llm_config(self):
        async with self.Session() as session:
            result = await session.execute(select(LLMConfig))
            return result.scalars().first()

    async def add_user(self, user: User):
        async with self.Session() as session:
            session.add(user)
            await session.commit()

    async def update_user(self, user: User):
        async with self.Session() as session:
            session.merge(user)
            await session.commit()

    async def get_user(self, user_id: int) -> User | None:
        async with self.Session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalars().first()

    async def add_chat_session(self, chat_session: ChatSession):
        async with self.Session() as session:
            session.add(chat_session)
            await session.commit()

    async def update_chat_session(self, chat_session: ChatSession):
        async with self.Session() as session:
            session.merge(chat_session)
            await session.commit()

    async def get_chat_session(self, chat_id: int) -> ChatSession | None:
        async with self.Session() as session:
            result = await session.execute(
                select(ChatSession).where(ChatSession.chat_id == chat_id)
            )
            return result.scalars().first()
