import json
from src.core.middleware import CalculationContext
from src.db.models import CalculationHistory

def test_save_calculation_context_success(repo, db_session):
    # Setup CalculationContext
    ctx = CalculationContext("2 + 2", {"x": 1.0})
    ctx.result = 4.0
    ctx.execution_time_ms = 12.5
    ctx.metadata["cached"] = True

    # Save
    saved_record = repo.save(ctx)

    # Verify return value
    assert saved_record.id is not None
    assert saved_record.expression == "2 + 2"
    assert json.loads(saved_record.variables_json) == {"x": 1.0}
    assert saved_record.result == 4.0
    assert saved_record.error is None
    assert saved_record.execution_time_ms == 12.5
    assert saved_record.cached is True
    assert saved_record.created_at is not None

    # Verify query in database
    db_record = db_session.get(CalculationHistory, saved_record.id)
    assert db_record is not None
    assert db_record.expression == "2 + 2"
    assert db_record.result == 4.0

def test_save_calculation_context_error(repo, db_session):
    # Setup error context
    ctx = CalculationContext("10 / 0", {})
    ctx.error = ZeroDivisionError("division by zero")
    ctx.execution_time_ms = 1.2
    ctx.metadata["cached"] = False

    # Save
    saved_record = repo.save(ctx)

    # Verify fields
    assert saved_record.id is not None
    assert saved_record.expression == "10 / 0"
    assert saved_record.result is None
    assert "division by zero" in saved_record.error
    assert saved_record.execution_time_ms == 1.2
    assert saved_record.cached is False

    db_record = db_session.get(CalculationHistory, saved_record.id)
    assert db_record is not None
    assert db_record.result is None
    assert "division by zero" in db_record.error

def test_get_by_expression(repo):
    # Save a few calculations
    ctx1 = CalculationContext("2 + 2")
    ctx1.result = 4.0
    repo.save(ctx1)

    ctx2 = CalculationContext("3 * 3")
    ctx2.result = 9.0
    repo.save(ctx2)

    ctx3 = CalculationContext("2 + 2")
    ctx3.result = 5.0  # maybe different result or rerun
    repo.save(ctx3)

    # Query by expression
    results_2_plus_2 = repo.get_by_expression("2 + 2")
    assert len(results_2_plus_2) == 2
    assert all(r.expression == "2 + 2" for r in results_2_plus_2)

    results_3_mul_3 = repo.get_by_expression("3 * 3")
    assert len(results_3_mul_3) == 1
    assert results_3_mul_3[0].result == 9.0

def test_get_recent_limit_and_order(repo):
    # Save 5 calculations with increasing execution times to verify order/limit
    for i in range(10):
        ctx = CalculationContext(f"1 + {i}")
        ctx.result = float(1 + i)
        repo.save(ctx)

    recent = repo.get_recent(limit=5)
    assert len(recent) == 5
    # Order should be descending (most recent first)
    assert recent[0].expression == "1 + 9"
    assert recent[4].expression == "1 + 5"

def test_get_stats_empty(repo):
    stats = repo.get_stats()
    assert stats == {
        "total": 0,
        "avg_time": 0.0,
        "error_rate": 0.0
    }

def test_get_stats(repo):
    # Setup stats: 4 calculations, 1 error, avg_time = (10 + 20 + 30 + 40)/4 = 25
    calculations = [
        ("1 + 1", 2.0, None, 10.0),
        ("2 + 2", 4.0, None, 20.0),
        ("3 / 0", None, ZeroDivisionError("division by zero"), 30.0),
        ("4 + 4", 8.0, None, 40.0),
    ]

    for expr, res, err, time_ms in calculations:
        ctx = CalculationContext(expr)
        ctx.result = res
        ctx.error = err
        ctx.execution_time_ms = time_ms
        repo.save(ctx)

    stats = repo.get_stats()
    assert stats["total"] == 4
    assert stats["avg_time"] == 25.0
    assert stats["error_rate"] == 0.25
