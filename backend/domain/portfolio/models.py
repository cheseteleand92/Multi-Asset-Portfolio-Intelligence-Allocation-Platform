from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    positions: Mapped[list["Position"]] = relationship("Position", back_populates="portfolio",
                                                        cascade="all, delete-orphan")


class Position(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(50), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(50), default="Equity")
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    cost_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(),
                                                  onupdate=func.now())
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")
