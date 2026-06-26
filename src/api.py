import json
from contextlib import asynccontextmanager
from typing import Dict, Optional, Any, List
from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.services.calculator import CalculatorService, CalculationConfig
from src.db.database import init_db, get_session
from src.db.repository import HistoryRepository

# Run init_db on application startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="MockProj API", lifespan=lifespan)

# Instantiate the CalculatorService with default settings
config = CalculationConfig(
    precision=4,
    enable_cache=True,
    cache_size=128,
    latency_simulation=0.0
)
calculator_service = CalculatorService(config)

class CalculateRequest(BaseModel):
    expression: str
    variables: Optional[Dict[str, float]] = None

@app.post("/calculate")
async def calculate(payload: CalculateRequest, db: Session = Depends(get_session)):
    repo = HistoryRepository(db)
    ctx = await calculator_service.calculate_async(
        expression=payload.expression,
        variables=payload.variables,
        repo=repo
    )
    if ctx.error:
        raise HTTPException(status_code=400, detail=str(ctx.error))
    
    return {
        "expression": ctx.expression,
        "variables": ctx.variables,
        "result": ctx.result,
        "execution_time_ms": ctx.execution_time_ms,
        "cached": ctx.metadata.get("cached", False)
    }

@app.get("/history")
def get_history(
    limit: int = Query(20, ge=1),
    expression: Optional[str] = Query(None),
    db: Session = Depends(get_session)
):
    repo = HistoryRepository(db)
    if expression:
        records = repo.get_by_expression(expression)
    else:
        records = repo.get_recent(limit)

    result = []
    for r in records:
        try:
            vars_dict = json.loads(r.variables_json) if r.variables_json else {}
        except Exception:
            vars_dict = {}
        result.append({
            "id": r.id,
            "expression": r.expression,
            "variables": vars_dict,
            "result": r.result,
            "error": r.error,
            "execution_time_ms": r.execution_time_ms,
            "cached": r.cached,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    return result

@app.get("/stats")
def get_stats(db: Session = Depends(get_session)):
    repo = HistoryRepository(db)
    db_stats = repo.get_stats()
    service_stats = calculator_service.get_stats()
    return {
        **db_stats,
        **service_stats
    }
