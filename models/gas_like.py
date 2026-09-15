from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class GasLike(Base):
    __tablename__ = "gas_likes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), nullable=False)
    gas_id: Mapped[int] = mapped_column(ForeignKey("gases.id"), nullable=False)
