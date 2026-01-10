from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base


class AIProvider(Base):
    __tablename__ = "ai_providers"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    base_url: Mapped[str] = mapped_column(String(500))
    api_key: Mapped[str] = mapped_column(String(500))
    models: Mapped[list[str]] = mapped_column(JSON, default=list)
