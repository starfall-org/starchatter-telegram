from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass


class LLMConfig(Base):
    __tablename__ = "llm_config"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model: Mapped[str] = mapped_column(String(100), nullable=True)
    instructions: Mapped[str] = mapped_column(String(10000), nullable=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("llm_provider.id"), nullable=True
    )
    provider: Mapped["LLMProvider"] = relationship("LLMProvider", backref="llm_config")


class LLMProvider(Base):
    __tablename__ = "llm_provider"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    api_key: Mapped[str] = mapped_column(String(100))
    base_url: Mapped[str] = mapped_column(String(100))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(unique=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    full_name: Mapped[str] = mapped_column(String(100))
    channels: Mapped[list["Channel"]] = relationship(
        "Channel", backref="owner", cascade="all, delete-orphan"
    )


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=True)
    owner: Mapped["User"] = relationship(User, backref="channels")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class UserChat(Base):
    __tablename__ = "user_chats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column()
    chat_id: Mapped[int] = mapped_column()
    chat_history: Mapped[list["ChatHistory"]] = relationship(
        "ChatHistory", backref="user_chat", cascade="all, delete-orphan"
    )


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(String(10000))
    user_chat: Mapped["UserChat"] = relationship(UserChat, backref="chat_history")
    user_chat_id: Mapped[int] = mapped_column(ForeignKey("user_chats.id"))
