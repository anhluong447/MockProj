from datetime import datetime, timezone
from sqlalchemy import String, Float, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class CalculationHistory(Base):
    __tablename__ = "calculation_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    expression: Mapped[str] = mapped_column(String, nullable=False)
    variables_json: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    cached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
