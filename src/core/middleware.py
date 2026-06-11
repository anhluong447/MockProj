import asyncio
import time
import logging
from typing import Callable, Dict, Any, List, Awaitable

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MathPipeline")

class CalculationContext:
    """Carries the state of a single mathematical calculation through the middleware pipeline."""
    def __init__(self, expression: str, variables: Dict[str, float] = None):
        self.expression = expression
        self.variables = variables or {}
        self.result: float = None
        self.error: Exception = None
        self.metadata: Dict[str, Any] = {}
        self.execution_time_ms: float = 0.0

class Middleware:
    """Base class for math engine middleware."""
    async def process(self, context: CalculationContext, next_call: Callable[[CalculationContext], Awaitable[CalculationContext]]) -> CalculationContext:
        return await next_call(context)

class LoggingMiddleware(Middleware):
    """Logs the execution details, status, and duration of calculations."""
    async def process(self, context: CalculationContext, next_call: Callable[[CalculationContext], Awaitable[CalculationContext]]) -> CalculationContext:
        start_time = time.perf_counter()
        logger.info(f"Pipeline started for expression: '{context.expression}' with variables {context.variables}")
        
        try:
            context = await next_call(context)
            if context.error:
                logger.error(f"Pipeline completed with error: {context.error}")
            else:
                logger.info(f"Pipeline completed. Result: {context.result}")
            return context
        finally:
            duration = (time.perf_counter() - start_time) * 1000.0
            context.execution_time_ms = duration
            logger.info(f"Calculation took {duration:.3f} ms")

class CachingMiddleware(Middleware):
    """Caches calculation results based on expression and variables."""
    def __init__(self, max_size: int = 128):
        self.cache: Dict[tuple, float] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def _get_cache_key(self, context: CalculationContext) -> tuple:
        # Normalize variables dict to a sorted tuple of pairs
        vars_tuple = tuple(sorted(context.variables.items()))
        return (context.expression.strip(), vars_tuple)

    async def process(self, context: CalculationContext, next_call: Callable[[CalculationContext], Awaitable[CalculationContext]]) -> CalculationContext:
        key = self._get_cache_key(context)
        if key in self.cache:
            self.hits += 1
            context.result = self.cache[key]
            context.metadata["cached"] = True
            logger.info(f"Cache HIT for: '{context.expression}'")
            return context
        
        self.misses += 1
        context = await next_call(context)
        
        # If it was successful, cache it
        if not context.error and context.result is not None:
            if len(self.cache) >= self.max_size:
                # Evict first element (FIFO eviction for simplicity)
                first_key = next(iter(self.cache))
                del self.cache[first_key]
            self.cache[key] = context.result
            context.metadata["cached"] = False
            
        return context

class ValidationMiddleware(Middleware):
    """Validates math safety parameters, protecting against huge inputs/outputs or division by zero."""
    def __init__(self, max_expression_length: int = 500, max_value_limit: float = 1e15):
        self.max_expression_length = max_expression_length
        self.max_value_limit = max_value_limit

    async def process(self, context: CalculationContext, next_call: Callable[[CalculationContext], Awaitable[CalculationContext]]) -> CalculationContext:
        # Pre-check: Expression length
        if len(context.expression) > self.max_expression_length:
            context.error = ValueError(f"Expression exceeds maximum allowed length of {self.max_expression_length} chars.")
            return context

        # Pre-check: Variable values
        for name, val in context.variables.items():
            if abs(val) > self.max_value_limit:
                context.error = ValueError(f"Variable '{name}' value {val} exceeds the safety limit of {self.max_value_limit}.")
                return context

        context = await next_call(context)

        # Post-check: Result value
        if not context.error and context.result is not None:
            if abs(context.result) > self.max_value_limit:
                context.error = ValueError(f"Calculation result {context.result} exceeds the safety limit of {self.max_value_limit}.")
                context.result = None

        return context

class LatencySimulationMiddleware(Middleware):
    """Simulates realistic computation latency for test or demo purposes."""
    def __init__(self, latency_seconds: float = 0.1):
        self.latency_seconds = latency_seconds

    async def process(self, context: CalculationContext, next_call: Callable[[CalculationContext], Awaitable[CalculationContext]]) -> CalculationContext:
        if self.latency_seconds > 0:
            await asyncio.sleep(self.latency_seconds)
        return await next_call(context)

class CalculationPipeline:
    """Orchestrates the execution of a list of middlewares around a core calculation function."""
    def __init__(self, middlewares: List[Middleware] = None):
        self.middlewares = middlewares or []

    def add_middleware(self, middleware: Middleware):
        self.middlewares.append(middleware)

    async def execute(self, context: CalculationContext, core_eval: Callable[[CalculationContext], float]) -> CalculationContext:
        # Build the onion pipeline execution structure
        async def dispatch(index: int, ctx: CalculationContext) -> CalculationContext:
            if index < len(self.middlewares):
                middleware = self.middlewares[index]
                # Define next call as calling the next middleware in line
                async def next_call(curr_ctx: CalculationContext) -> CalculationContext:
                    return await dispatch(index + 1, curr_ctx)
                return await middleware.process(ctx, next_call)
            else:
                # Core evaluation function
                try:
                    ctx.result = core_eval(ctx)
                except Exception as e:
                    ctx.error = e
                return ctx

        return await dispatch(0, context)
