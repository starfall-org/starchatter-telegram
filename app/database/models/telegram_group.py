from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.group_member import GroupMember
    from app.database.models.telegram_user import TelegramUser


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
