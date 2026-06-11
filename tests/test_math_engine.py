import unittest
import asyncio
import math
from src.core.expression_parser import ExpressionParser, ParserError, parse_and_evaluate
from src.core.middleware import CalculationContext, CalculationPipeline, ValidationMiddleware, CachingMiddleware
from src.services.calculator import CalculatorService, CalculationConfig
from src.services.task_queue import TaskQueueService, TaskStatus

class TestExpressionParser(unittest.TestCase):
    def test_basic_arithmetic(self):
        self.assertEqual(parse_and_evaluate("3 + 4 * 2"), 11.0)
        self.assertEqual(parse_and_evaluate("(3 + 4) * 2"), 14.0)
        self.assertEqual(parse_and_evaluate("10 / 2 - 1"), 4.0)
        self.assertEqual(parse_and_evaluate("2 ^ 3 ^ 2"), 512.0)  # Right associative check: 2 ^ (3 ^ 2) = 2 ^ 9 = 512

    def test_unary_operators(self):
        self.assertEqual(parse_and_evaluate("-5 + 10"), 5.0)
        self.assertEqual(parse_and_evaluate("-(3 + 2)"), -5.0)
        self.assertEqual(parse_and_evaluate("+5 * -2"), -10.0)

    def test_variables(self):
        vars_dict = {"x": 5.0, "y": 2.0}
        self.assertEqual(parse_and_evaluate("x * y + 3", vars_dict), 13.0)
        self.assertEqual(parse_and_evaluate("x ^ y", vars_dict), 25.0)
        with self.assertRaises(ParserError):
            parse_and_evaluate("x * z", vars_dict)  # z is undefined

    def test_functions(self):
        vars_dict = {"pi": math.pi}
        # sin(pi/2) = 1
        self.assertAlmostEqual(parse_and_evaluate("sin(pi / 2)", vars_dict), 1.0)
        self.assertEqual(parse_and_evaluate("sqrt(16)"), 4.0)
        self.assertEqual(parse_and_evaluate("abs(-10.5)"), 10.5)
        self.assertAlmostEqual(parse_and_evaluate("log(exp(5))"), 5.0)
        self.assertAlmostEqual(parse_and_evaluate("log(100, 10)"), 2.0)  # Log with custom base

    def test_invalid_syntax(self):
        with self.assertRaises(ParserError):
            parse_and_evaluate("3 + * 4")
        with self.assertRaises(ParserError):
            parse_and_evaluate("sqrt(1, 2, 3)")  # sqrt only takes 1 argument
        with self.assertRaises(ZeroDivisionError):
            parse_and_evaluate("10 / 0")

class TestCalculatorPipeline(unittest.IsolatedAsyncioTestCase):
    async def test_calculator_service_async(self):
        cfg = CalculationConfig(precision=3, latency_simulation=0.0)
        calc = CalculatorService(cfg)
        
        # Async calculation
        ctx = await calc.calculate_async("sqrt(x) + y", {"x": 9.0, "y": 1.5})
        self.assertIsNone(ctx.error)
        self.assertEqual(ctx.result, 4.5)
        
        # Test Caching
        ctx2 = await calc.calculate_async("sqrt(x) + y", {"x": 9.0, "y": 1.5})
        self.assertTrue(ctx2.metadata.get("cached"))
        self.assertEqual(ctx2.result, 4.5)
        
        stats = calc.get_stats()
        self.assertEqual(stats["cache_hits"], 1)

    async def test_validation_middleware(self):
        cfg = CalculationConfig(precision=4, max_value_limit=100.0, latency_simulation=0.0)
        calc = CalculatorService(cfg)
        
        # Exceeds max value limit
        ctx = await calc.calculate_async("150")
        self.assertIsNotNone(ctx.error)
        self.assertIn("exceeds the safety limit", str(ctx.error))
        
        # Expression length limit
        cfg_long = CalculationConfig(max_expression_length=5)
        calc_long = CalculatorService(cfg_long)
        ctx_long = await calc_long.calculate_async("1 + 2 + 3")
        self.assertIsNotNone(ctx_long.error)
        self.assertIn("exceeds maximum allowed length", str(ctx_long.error))

class TestTaskQueueService(unittest.IsolatedAsyncioTestCase):
    async def test_task_queue_execution(self):
        cfg = CalculationConfig(precision=4, latency_simulation=0.01)
        calc = CalculatorService(cfg)
        
        # Create TaskQueueService
        queue_service = TaskQueueService(
            pipeline=calc.pipeline,
            core_evaluator=calc._core_eval,
            num_workers=2
        )
        
        await queue_service.start()
        
        try:
            # Submit several tasks
            tid1 = queue_service.submit_task("2 ^ 10")
            tid2 = queue_service.submit_task("sin(x)", {"x": 0.0})
            tid3 = queue_service.submit_task("10 / 0")  # will fail
            
            # Wait for all to finish
            await queue_service.wait_all()
            
            t1 = queue_service.get_task(tid1)
            t2 = queue_service.get_task(tid2)
            t3 = queue_service.get_task(tid3)
            
            self.assertEqual(t1.status, TaskStatus.COMPLETED)
            self.assertEqual(t1.result, 1024.0)
            
            self.assertEqual(t2.status, TaskStatus.COMPLETED)
            self.assertEqual(t2.result, 0.0)
            
            self.assertEqual(t3.status, TaskStatus.FAILED)
            self.assertIsNotNone(t3.error)
            self.assertIn("ZeroDivisionError", t3.error)
            
            metrics = queue_service.get_metrics()
            self.assertEqual(metrics["processed_tasks"], 2)
            self.assertEqual(metrics["failed_tasks"], 1)
            
        finally:
            await queue_service.stop()

if __name__ == "__main__":
    unittest.main()
