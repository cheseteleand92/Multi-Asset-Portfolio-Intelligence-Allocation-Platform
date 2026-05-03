from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(50), index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    signal_type: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    regime: Mapped[str] = mapped_column(String(20), default="unknown")
