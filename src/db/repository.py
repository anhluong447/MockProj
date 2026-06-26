import json
from typing import List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.db.models import CalculationHistory
from src.core.middleware import CalculationContext

class HistoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, ctx: CalculationContext) -> CalculationHistory:
        """Saves a CalculationContext to the database."""
        variables_json = json.dumps(ctx.variables)
        error_str = str(ctx.error) if ctx.error is not None else None
        cached = bool(ctx.metadata.get("cached", False))

        record = CalculationHistory(
            expression=ctx.expression,
            variables_json=variables_json,
            result=ctx.result,
            error=error_str,
            execution_time_ms=ctx.execution_time_ms,
            cached=cached
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_by_expression(self, expr: str) -> List[CalculationHistory]:
        """Retrieves history records filtered by expression name."""
        stmt = select(CalculationHistory).where(CalculationHistory.expression == expr)
        return list(self.session.scalars(stmt).all())

    def get_recent(self, limit: int = 50) -> List[CalculationHistory]:
        """Retrieves recent calculation records."""
        stmt = select(CalculationHistory).order_by(
            CalculationHistory.created_at.desc(),
            CalculationHistory.id.desc()
        ).limit(limit)
        return list(self.session.scalars(stmt).all())

    def get_stats(self) -> Dict[str, Any]:
        """Computes statistical details over all stored calculations."""
        total = self.session.scalar(select(func.count(CalculationHistory.id))) or 0
        if total == 0:
            return {
                "total": 0,
                "avg_time": 0.0,
                "error_rate": 0.0
            }

        avg_time = self.session.scalar(select(func.avg(CalculationHistory.execution_time_ms))) or 0.0
        error_count = self.session.scalar(
            select(func.count(CalculationHistory.id)).where(CalculationHistory.error.isnot(None))
        ) or 0

        return {
            "total": total,
            "avg_time": float(avg_time),
            "error_rate": float(error_count) / float(total)
        }
