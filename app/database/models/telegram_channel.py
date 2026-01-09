from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.channel_member import ChannelMember
    from app.database.models.telegram_user import TelegramUser


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
