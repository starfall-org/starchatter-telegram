from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column()
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", backref="chat_session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(String(10000))
    chat_session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"))
    chat_session: Mapped[ChatSession] = relationship("ChatSession", backref="messages")
