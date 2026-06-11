import asyncio
import time
from src.services.calculator import CalculatorService, CalculationConfig
from src.services.task_queue import TaskQueueService, TaskStatus

def helper_format(value: float) -> str:
    return f"Result: {value}"

class Application:
    def __init__(self):
        # Configuration with latency simulation enabled for the demo to show concurrency
        self.cfg = CalculationConfig(
            precision=4,
            enable_cache=True,
            cache_size=64,
            latency_simulation=0.08  # 80ms artificial delay to demonstrate worker concurrency
        )
        self.calc = CalculatorService(self.cfg)
        
        # Initialize background task queue service with 3 concurrent workers
        self.queue_service = TaskQueueService(
            pipeline=self.calc.pipeline,
            core_evaluator=self.calc._core_eval,
            num_workers=3
        )

    async def on_startup(self):
        print("=" * 60)
        print("      ENTERPRISE MATHEMATICAL CALCULATION ENGINE STARTED      ")
        print("=" * 60)
        
        # 1. Backward compatibility demo
        print("\n--- [Step 1] Running Legacy Arithmetic Demo ---")
        res1 = self.calc.add(10.5, 2.5)
        res2 = self.calc.multiply(3, 4)
        print(helper_format(res1))
        print(helper_format(res2))

        # 2. Expression Parsing & Evaluation
        print("\n--- [Step 2] Complex Expression Evaluation Demo ---")
        expr = "sin(x) * 2 + sqrt(y) ^ 2"
        variables = {"x": 1.570796, "y": 9.0}  # x is approx pi/2
        print(f"Evaluating formula: '{expr}' where variables = {variables}")
        
        # Synchronous execution
        sync_res = self.calc.calculate_sync(expr, variables)
        print(f"Sync result (no middlewares): {sync_res}")

        # 3. Middleware Pipeline & Caching Demo
        print("\n--- [Step 3] Middleware & Caching Pipeline Demo ---")
        # Run async calculation (first run, should miss cache)
        print("First execution (cold cache)...")
        ctx1 = await self.calc.calculate_async(expr, variables)
        print(f"Result 1: {ctx1.result} (Cached: {ctx1.metadata.get('cached')}) - Time: {ctx1.execution_time_ms:.2f} ms")

        # Run async calculation (second run, should hit cache)
        print("Second execution (hot cache)...")
        ctx2 = await self.calc.calculate_async(expr, variables)
        print(f"Result 2: {ctx2.result} (Cached: {ctx2.metadata.get('cached')}) - Time: {ctx2.execution_time_ms:.2f} ms")

        # 4. Input Validation & Error Handling Demo
        print("\n--- [Step 4] Pipeline Security & Validation Demo ---")
        # Example A: Division by zero
        ctx_div = await self.calc.calculate_async("10 / (5 - 5)")
        print(f"Error handling A ('10 / (5 - 5)'): error={ctx_div.error}")

        # Example B: Safety overflow limit
        ctx_overflow = await self.calc.calculate_async("10 ^ 20")
        print(f"Error handling B ('10 ^ 20'): error={ctx_overflow.error}")

        # 5. Background Async Worker Task Queue Demo
        print("\n--- [Step 5] Asynchronous Task Queue & Worker Pool Demo ---")
        await self.queue_service.start()

        # Submit different tasks
        tasks_to_submit = [
            ("log(100, 10) + abs(-5)", {}),
            ("x * 2.5", {"x": 12.0}),
            ("sin(pi) + cos(pi)", {"pi": 3.14159}),
            ("sqrt(y) / (x - 2)", {"x": 2.0, "y": 16.0}),  # Will fail: division by zero
            ("2 ^ 8 * sqrt(256)", {}),
            ("exp(2)", {})
        ]

        print(f"Submitting {len(tasks_to_submit)} tasks to the Queue...")
        task_ids = []
        for formula, vars_ in tasks_to_submit:
            tid = self.queue_service.submit_task(formula, vars_)
            task_ids.append(tid)
            print(f"Submitted task: {tid[:8]}... -> '{formula}'")

        # Wait for all tasks to complete
        print("\nWaiting for all tasks to be processed by workers...")
        start_wait = time.perf_counter()
        await self.queue_service.wait_all()
        end_wait = time.perf_counter()

        print(f"All tasks processed in {(end_wait - start_wait)*1000:.2f} ms\n")
        print("Results:")
        for tid in task_ids:
            task = self.queue_service.get_task(tid)
            status_str = f"[{task.status}]"
            if task.status == TaskStatus.COMPLETED:
                print(f"  Task {task.id[:8]}: {task.expression} = {task.result} (took {task.duration_ms:.2f} ms)")
            else:
                print(f"  Task {task.id[:8]}: {task.expression} -> FAILED: {task.error}")

        # Stop background workers
        await self.queue_service.stop()

        # Print final report
        print("\n" + "=" * 60)
        print("                SYSTEM METRICS & TELEMETRY REPORT              ")
        print("=" * 60)
        calc_stats = self.calc.get_stats()
        queue_metrics = self.queue_service.get_metrics()

        print(f"Calculator Service Stats:")
        print(f"  Total calculations: {calc_stats['total_operations_performed']}")
        print(f"  Cache hits:         {calc_stats['cache_hits']}")
        print(f"  Cache misses:       {calc_stats['cache_misses']}")
        print(f"  Active cache items: {calc_stats['cache_size']}")
        print(f"\nTask Queue Metrics:")
        print(f"  Workers spawned:    {queue_metrics['num_workers']}")
        print(f"  Processed jobs:     {queue_metrics['processed_tasks']}")
        print(f"  Failed jobs:        {queue_metrics['failed_tasks']}")
        print(f"  Average worker latency: {queue_metrics['average_latency_ms']:.2f} ms")
        print("=" * 60)

if __name__ == "__main__":
    app = Application()
    asyncio.run(app.on_startup())
