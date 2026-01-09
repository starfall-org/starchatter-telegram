from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base


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
