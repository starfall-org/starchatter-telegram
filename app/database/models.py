from sqlalchemy import Boolean, ForeignKey, String, BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --- Association tables (với cờ is_admin, is_owner) ---


class GroupMember(Base):
    __tablename__ = "group_members"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_users.id"), primary_key=True
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_groups.id"), primary_key=True
    )
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["TelegramUser"] = relationship(back_populates="group_links")
    group: Mapped["TelegramGroup"] = relationship(back_populates="user_links")


class ChannelMember(Base):
    __tablename__ = "channel_members"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_users.id"), primary_key=True
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_channels.id"), primary_key=True
    )
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["TelegramUser"] = relationship(back_populates="channel_links")
    channel: Mapped["TelegramChannel"] = relationship(back_populates="user_links")


# --- Main entities ---


class TelegramUser(Base):
    __tablename__ = "telegram_users"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100), nullable=True)

    group_links: Mapped[list["GroupMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    channel_links: Mapped[list["ChannelMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    groups: Mapped[list["TelegramGroup"]] = relationship(
        secondary="group_members", viewonly=True
    )
    channels: Mapped[list["TelegramChannel"]] = relationship(
        secondary="channel_members", viewonly=True
    )


class TelegramGroup(Base):
    __tablename__ = "telegram_groups"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    title: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=True)
    disable_chatbot: Mapped[bool] = mapped_column(Boolean, default=False)
    disable_anti_spam: Mapped[bool] = mapped_column(Boolean, default=False)
    user_links: Mapped[list["GroupMember"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    users: Mapped[list["TelegramUser"]] = relationship(
        secondary="group_members", viewonly=True
    )


class TelegramChannel(Base):
    __tablename__ = "telegram_channels"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    title: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=True)

    user_links: Mapped[list["ChannelMember"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )
    users: Mapped[list["TelegramUser"]] = relationship(
        secondary="channel_members", viewonly=True
    )


class MutedCase(Base):
    __tablename__ = "muted_cases"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    group_id: Mapped[int] = mapped_column(BigInteger)
    group_title: Mapped[str] = mapped_column(String(255))
    group_username: Mapped[str] = mapped_column(String(32), nullable=True)
    reason: Mapped[str] = mapped_column(String(1000))
    content: Mapped[str] = mapped_column(String(4000))
