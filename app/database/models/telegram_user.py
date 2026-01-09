from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.group_member import GroupMember
    from app.database.models.channel_member import ChannelMember
    from app.database.models.telegram_group import TelegramGroup
    from app.database.models.telegram_channel import TelegramChannel


class TelegramUser(Base):
    __tablename__ = "telegram_users"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100), nullable=True)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False)

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
