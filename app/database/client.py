import asyncio
from datetime import datetime, timedelta

from config import TURSO_AUTH_TOKEN, TURSO_DB_URL
from database.models import Base
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker


class Database:
    _instance = None
    _timeout = timedelta(minutes=5)
    _initialized_db = False  # thêm cờ kiểm soát init db

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._engine = None
        self._sessionmaker = None
        self._session = None
        self._disposed = True
        self._last_used = datetime.now()
        self._closing_task = asyncio.create_task(self._auto_close())
        self._initialized = True

    def _create_engine(self):
        self._engine = create_engine(
            TURSO_DB_URL,
            connect_args={"auth_token": TURSO_AUTH_TOKEN} if TURSO_AUTH_TOKEN else {},
        )
        self._sessionmaker = sessionmaker(self._engine, expire_on_commit=False)
        self._disposed = False

    def init_db(self):
        """Tạo bảng nếu chưa tồn tại, chỉ chạy một lần khi khởi động."""
        if not self._initialized_db:
            if self._disposed or self._engine is None:
                self._create_engine()
            # tạo bảng trong luồng riêng để tránh block event loop
            if self._engine:
                Base.metadata.create_all(self._engine)
                self._initialized_db = True

    def _get_session(self) -> Session | None:
        if self._disposed or self._engine is None:
            self._create_engine()
        self._last_used = datetime.now()
        if self._session is None or not self._session.is_active:
            if self._sessionmaker:
                self._session = self._sessionmaker()
        if self._session:
            return self._session

    async def _auto_close(self):
        while True:
            await asyncio.sleep(60)
            now = datetime.now()
            if self._session and (now - self._last_used > self._timeout):
                await asyncio.to_thread(self._session.close)
                self._session = None
            if (
                not self._disposed
                and self._engine
                and (now - self._last_used > self._timeout)
            ):
                self._engine.dispose()
                self._disposed = True

    @property
    def engine(self):
        if self._disposed:
            self._create_engine()
        return self._engine

    async def _run_in_session(self, func, *args, **kwargs):
        s = self._get_session()
        self._last_used = datetime.now()
        try:
            return await asyncio.to_thread(func, s, *args, **kwargs)
        finally:
            pass

    async def get(self, model, *args, **kwargs):
        return await self.execute(select(model).filter_by(*args, **kwargs))

    async def add(self, obj):
        await self._run_in_session(lambda s, o: (s.add(o), s.commit()), obj)

    async def delete(self, obj):
        await self._run_in_session(lambda s, o: (s.delete(o), s.commit()), obj)

    async def merge(self, obj):
        await self._run_in_session(lambda s, o: (s.merge(o), s.commit()), obj)

    async def commit(self):
        await self._run_in_session(lambda s: s.commit())

    async def execute(self, *args, **kwargs):
        return await self._run_in_session(lambda s: s.execute(*args, **kwargs))
