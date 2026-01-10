from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base


class DefaultModel(Base):
    __tablename__ = "default_models"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    feature: Mapped[str] = mapped_column(String(50), unique=True)  # chat, translate, poem, image, etc.
    provider_name: Mapped[str] = mapped_column(String(50), nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
