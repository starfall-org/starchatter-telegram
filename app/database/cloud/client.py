
import asyncio
from datetime import datetime, timedelta

from config import TURSO_AUTH_TOKEN, TURSO_DB_URL
from database.local import local_db
from database.models import AIProvider, DefaultModel, TelegramUser, Base
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker


class CloudDatabase:
    """LibSQL Cloud database"""

    _instance = None
    _timeout = timedelta(minutes=5)
    _initialized_db = False

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
        # Mirror to local database
        await local_db.add(obj)

    async def add_all(self, objs):
        """Add multiple objects"""
        for obj in objs:
            await self.add(obj)

    async def delete(self, obj):
        await self._run_in_session(lambda s, o: (s.delete(o), s.commit()), obj)
        # Mirror to local database
        await local_db.delete(obj)

    async def merge(self, obj):
        await self._run_in_session(lambda s, o: (s.merge(o), s.commit()), obj)
        # Mirror to local database
        await local_db.merge(obj)

    async def commit(self):
        await self._run_in_session(lambda s: s.commit())
        # Mirror commit to local database
        await local_db.commit()

    async def execute(self, *args, **kwargs):
        return await self._run_in_session(lambda s: s.execute(*args, **kwargs))

    # AIProvider methods
    async def get_provider_by_name(self, name: str):
        """Lấy provider theo tên"""
        return await self.get(AIProvider, name=name)

    async def get_default_provider(self):
        """Lấy provider mặc định từ DefaultModel"""
        result = await self.execute(select(DefaultModel).filter_by(feature="default_provider"))
        default_model = result.scalars().first()
        if default_model and default_model.provider_name:
            return await self.get_provider_by_name(default_model.provider_name)
        return None

    async def set_default_provider(self, provider: AIProvider):
        """Đặt provider mặc định trong DefaultModel"""
        result = await self.execute(select(DefaultModel).filter_by(feature="default_provider"))
        default_model = result.scalars().first()
        
        if not default_model:
            default_model = DefaultModel(feature="default_provider", provider_name=provider.name)
            await self.add(default_model)
        else:
            default_model.provider_name = provider.name
            await self.commit()

    # DefaultModel methods
    async def get_default_model(self, feature: str):
        """Lấy model mặc định cho một feature"""
        result = await self.execute(select(DefaultModel).filter_by(feature=feature))
        return result.scalars().first()

    async def set_default_model(self, feature: str, provider_name: str = None, model: str = None, config: dict = None):
        """Đặt model mặc định cho một feature"""
        result = await self.execute(select(DefaultModel).filter_by(feature=feature))
        default_model = result.scalars().first()
        
        if not default_model:
            default_model = DefaultModel(
                feature=feature,
                provider_name=provider_name,
                model=model,
                config=config or {}
            )
            await self.add(default_model)
        else:
            if provider_name is not None:
                default_model.provider_name = provider_name
            if model is not None:
                default_model.model = model
            if config is not None:
                default_model.config = config
            await self.commit()

    # TelegramUser (Owner) methods
    async def get_user(self, user_id: int):
        """Lấy user theo user_id"""
        return await self.get(TelegramUser, id=user_id)

    async def is_owner(self, user_id: int) -> bool:
        """Kiểm tra user có phải là owner không"""
        user = await self.get_user(user_id)
        return user is not None and user.is_owner if user else False

    async def set_owner(self, user_id: int, is_owner: bool = True, username: str = None, full_name: str = None):
        """Đặt quyền owner cho user"""
        user = await self.get_user(user_id)
        if user:
            user.is_owner = is_owner
            if username:
                user.username = username
            if full_name:
                user.first_name = full_name
            await self.commit()
        else:
            # Tạo user mới
            first_name = full_name or ""
            user = TelegramUser(
                id=user_id,
                username=username,
                first_name=first_name,
                is_owner=is_owner,
            )
            await self.add(user)

    async def add_owner(self, user_id: int, username: str = None, full_name: str = None):
        """Thêm owner mới"""
        await self.set_owner(user_id, True, username, full_name)

    async def remove_owner(self, user_id: int):
        """Xóa quyền owner"""
        await self.set_owner(user_id, False)

    async def get_all_owners(self):
        """Lấy tất cả owners"""
        result = await self.execute(select(TelegramUser).filter_by(is_owner=True))
        return result.scalars().all()


# Global instance
cloud_db = CloudDatabase()
