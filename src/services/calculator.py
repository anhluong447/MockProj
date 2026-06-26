import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from src.core.base import BaseService
from src.core.expression_parser import parse_and_evaluate, ExpressionParser
from src.core.middleware import (
    CalculationPipeline, CalculationContext, LoggingMiddleware,
    CachingMiddleware, ValidationMiddleware, LatencySimulationMiddleware
)

@dataclass
class CalculationConfig:
    precision: int = 4
    use_gpu: bool = False
    allowed_operations: list[str] = field(default_factory=lambda: ["add", "sub", "mul", "div", "pow"])
    enable_cache: bool = True
    cache_size: int = 128
    latency_simulation: float = 0.0
    max_expression_length: int = 500
    max_value_limit: float = 1e15

class CalculatorService(BaseService):
    """Enterprise-ready Mathematical Calculator with expression parsing, validation, caching and pipelines."""
    def __init__(self, config: CalculationConfig):
        super().__init__()
        self.name = "CalculatorService"
        self.config = config
        self.ops_count = 0
        self.active = True

        # Initialize Middleware Pipeline
        self.pipeline = CalculationPipeline()
        self.pipeline.add_middleware(LoggingMiddleware())
        
        if self.config.enable_cache:
            self.caching_mw = CachingMiddleware(max_size=self.config.cache_size)
            self.pipeline.add_middleware(self.caching_mw)
        else:
            self.caching_mw = None

        self.pipeline.add_middleware(ValidationMiddleware(
            max_expression_length=self.config.max_expression_length,
            max_value_limit=self.config.max_value_limit
        ))

        if self.config.latency_simulation > 0:
            self.pipeline.add_middleware(LatencySimulationMiddleware(self.config.latency_simulation))

    def _core_eval(self, ctx: CalculationContext) -> float:
        """Core sync evaluator parsing and evaluating the AST expression."""
        self.ops_count += 1
        # Use our ExpressionParser to build and evaluate the AST
        parser = ExpressionParser(ctx.expression)
        ast = parser.parse()
        raw_res = ast.evaluate(ctx.variables)
        
        # Round to configured precision
        return round(raw_res, self.config.precision)

    async def calculate_async(self, expression: str, variables: Optional[Dict[str, float]] = None,
                              repo: Optional[Any] = None) -> CalculationContext:
        """Asynchronously executes the math evaluation through the middleware pipeline."""
        context = CalculationContext(expression, variables)
        ctx = await self.pipeline.execute(context, self._core_eval)
        if repo:
            repo.save(ctx)
        return ctx

    def calculate_sync(self, expression: str, variables: Optional[Dict[str, float]] = None) -> float:
        """Synchronously executes the math evaluation bypassing async middleware (no caching/latency)."""
        self.ops_count += 1
        context = CalculationContext(expression, variables)
        return self._core_eval(context)

    # Legacy Methods for Backward Compatibility
    def add(self, a: float, b: float) -> float:
        """Synchronous add."""
        self.ops_count += 1
        return round(a + b, self.config.precision)

    def multiply(self, a: float, b: float) -> float:
        """Synchronous multiply."""
        self.ops_count += 1
        return round(a * b, self.config.precision)

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistical metadata of calculations."""
        stats = {
            "total_operations_performed": self.ops_count,
            "precision_digits": self.config.precision
        }
        if self.caching_mw:
            stats.update({
                "cache_hits": self.caching_mw.hits,
                "cache_misses": self.caching_mw.misses,
                "cache_size": len(self.caching_mw.cache)
            })
        return stats
