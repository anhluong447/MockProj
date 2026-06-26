import sys
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.middleware import (
    CalculationPipeline,
    CalculationContext,
    Middleware,
    LoggingMiddleware,
    CachingMiddleware,
    ValidationMiddleware,
    LatencySimulationMiddleware
)

@pytest.fixture
def pipeline():
    return CalculationPipeline()

class SimpleMiddleware(Middleware):
    async def process(self, context, next_call):
        context.metadata["visited"] = True
        return await next_call(context)

class ShortCircuitMiddleware(Middleware):
    async def process(self, context, next_call):
        context.result = 99.0
        context.metadata["skipped"] = True
        return context

class ErrorMiddleware(Middleware):
    async def process(self, context, next_call):
        raise RuntimeError("middleware error")

class LateErrorMiddleware(Middleware):
    async def process(self, context, next_call):
        raise ValueError("late error")

@pytest.mark.asyncio
async def test_empty_middleware_list_happy_path(pipeline):
    context = CalculationContext("2 + 2")
    core_eval = lambda ctx: 42.0
    result = await pipeline.execute(context, core_eval)
    assert result.result == 42.0
    assert result.error is None

@pytest.mark.asyncio
async def test_middleware_calls_next_correctly(pipeline):
    context = CalculationContext("2 + 2")
    core_eval = lambda ctx: 3.14
    middleware1 = SimpleMiddleware()
    pipeline.middlewares = [middleware1]
    result = await pipeline.execute(context, core_eval)
    assert result.metadata.get("visited") is True
    assert result.result == 3.14

@pytest.mark.asyncio
async def test_middleware_skips_next(pipeline):
    context = CalculationContext("2 + 2")
    core_eval = MagicMock(side_effect=RuntimeError("should not be called"))
    middleware = ShortCircuitMiddleware()
    pipeline.middlewares = [middleware]
    result = await pipeline.execute(context, core_eval)
    assert result.result == 99.0
    assert result.metadata.get("skipped") is True
    core_eval.assert_not_called()

@pytest.mark.asyncio
async def test_core_eval_raises_exception(pipeline):
    context = CalculationContext("2 + 2")
    def core_eval(ctx):
        raise ValueError("calc error")
    result = await pipeline.execute(context, core_eval)
    assert result.result is None
    assert isinstance(result.error, ValueError)
    assert str(result.error) == "calc error"

@pytest.mark.asyncio
async def test_middleware_raises_exception(pipeline):
    context = CalculationContext("2 + 2")
    core_eval = lambda ctx: 1.0
    middleware = ErrorMiddleware()
    pipeline.middlewares = [middleware]
    with pytest.raises(RuntimeError, match="middleware error"):
        await pipeline.execute(context, core_eval)

@pytest.mark.asyncio
async def test_multiple_middlewares_with_error_in_late_middleware(pipeline):
    context = CalculationContext("2 + 2")
    core_eval = MagicMock(side_effect=RuntimeError("should not be called"))
    m1 = SimpleMiddleware()
    m2 = LateErrorMiddleware()
    pipeline.middlewares = [m1, m2]
    with pytest.raises(ValueError, match="late error"):
        await pipeline.execute(context, core_eval)
    core_eval.assert_not_called()

@pytest.mark.asyncio
async def test_logging_middleware(pipeline):
    context = CalculationContext("2 + 2")
    pipeline.add_middleware(LoggingMiddleware())
    result = await pipeline.execute(context, lambda ctx: 4.0)
    assert result.result == 4.0
    assert result.execution_time_ms >= 0.0

@pytest.mark.asyncio
async def test_caching_middleware(pipeline):
    cache = CachingMiddleware()
    pipeline.add_middleware(cache)
    
    context1 = CalculationContext("2 + 2")
    result1 = await pipeline.execute(context1, lambda ctx: 4.0)
    assert result1.result == 4.0
    assert result1.metadata.get("cached") is False
    assert cache.misses == 1
    assert cache.hits == 0
    
    # Second execution should hit cache
    context2 = CalculationContext("2 + 2")
    result2 = await pipeline.execute(context2, lambda ctx: 4.0)
    assert result2.result == 4.0
    assert result2.metadata.get("cached") is True
    assert cache.misses == 1
    assert cache.hits == 1

@pytest.mark.asyncio
async def test_validation_middleware_expression_too_long(pipeline):
    val = ValidationMiddleware(max_expression_length=5)
    pipeline.add_middleware(val)
    
    context = CalculationContext("123456")
    result = await pipeline.execute(context, lambda ctx: 1.0)
    assert result.error is not None
    assert "exceeds maximum allowed length" in str(result.error)
    assert result.result is None

@pytest.mark.asyncio
async def test_validation_middleware_variable_limit(pipeline):
    val = ValidationMiddleware(max_value_limit=10.0)
    pipeline.add_middleware(val)
    
    context = CalculationContext("x", {"x": 20.0})
    result = await pipeline.execute(context, lambda ctx: 20.0)
    assert result.error is not None
    assert "exceeds the safety limit" in str(result.error)

@pytest.mark.asyncio
async def test_latency_middleware(pipeline):
    pipeline.add_middleware(LatencySimulationMiddleware(latency_seconds=0.01))
    context = CalculationContext("2 + 2")
    start_time = time.perf_counter()
    result = await pipeline.execute(context, lambda ctx: 4.0)
    duration = time.perf_counter() - start_time
    assert result.result == 4.0
    assert duration >= 0.01