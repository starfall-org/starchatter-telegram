from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base


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
