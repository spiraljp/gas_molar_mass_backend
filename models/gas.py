from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Gas(Base):
    __tablename__ = "gases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    gas_name: Mapped[str] = mapped_column(String(100), nullable=False)
    gas_formula: Mapped[str] = mapped_column(String(20), nullable=False)
    short_description: Mapped[str] = mapped_column(String(500), nullable=False)
    gas_status: Mapped[str] = mapped_column(String(20), nullable=False)
    gas_image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gas_video_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    molar_mass: Mapped[float | None] = mapped_column(Float, nullable=True)
    density_normal_conditions: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    formed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), nullable=False)
