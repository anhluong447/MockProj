import asyncio
import uuid
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from src.core.base import BaseService
from src.core.middleware import CalculationPipeline, CalculationContext

class TaskStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class CalculationTask:
    id: str
    expression: str
    variables: Dict[str, float] = field(default_factory=dict)
    status: str = TaskStatus.PENDING
    result: Optional[float] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: float = 0.0
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "expression": self.expression,
            "variables": self.variables,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "cached": self.cached
        }

class TaskQueueService(BaseService):
    """Asynchronous Queue Service to run background tasks with a configurable pool of worker threads."""
    def __init__(self, pipeline: CalculationPipeline, core_evaluator: Callable[[CalculationContext], float], num_workers: int = 3):
        super().__init__()
        self.name = "TaskQueueService"
        self.pipeline = pipeline
        self.core_evaluator = core_evaluator
        self.num_workers = num_workers
        
        self._queue: asyncio.Queue[CalculationTask] = asyncio.Queue()
        self._tasks_registry: Dict[str, CalculationTask] = {}
        self._workers: List[asyncio.Task] = []
        self._completed_events: Dict[str, asyncio.Event] = {}
        
        # Metrics
        self.processed_count = 0
        self.failed_count = 0
        self.total_latency_ms = 0.0

    async def start(self):
        """Starts the background workers."""
        if self.active:
            return
        
        self.active = True
        self._workers = [
            asyncio.create_task(self._worker_loop(i))
            for i in range(self.num_workers)
        ]
        print(f"[{self.name}] Started {self.num_workers} background workers.")

    async def stop(self):
        """Stops the background workers and waits for queue drain."""
        if not self.active:
            return
        
        self.active = False
        # Cancel workers
        for worker in self._workers:
            worker.cancel()
        
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        print(f"[{self.name}] Stopped workers.")

    def submit_task(self, expression: str, variables: Optional[Dict[str, float]] = None) -> str:
        """Submits a math task to the queue, returning the unique task ID."""
        task_id = str(uuid.uuid4())
        task = CalculationTask(
            id=task_id,
            expression=expression,
            variables=variables or {}
        )
        self._tasks_registry[task_id] = task
        self._completed_events[task_id] = asyncio.Event()
        self._queue.put_nowait(task)
        return task_id

    def get_task(self, task_id: str) -> Optional[CalculationTask]:
        """Queries the status and result of a task."""
        return self._tasks_registry.get(task_id)

    def get_all_tasks(self) -> List[CalculationTask]:
        """Returns all registered tasks."""
        return list(self._tasks_registry.values())

    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> CalculationTask:
        """Blocks until the task is complete (or failed), or timeout is reached."""
        if task_id not in self._tasks_registry:
            raise KeyError(f"Task with ID {task_id} not found.")
            
        event = self._completed_events[task_id]
        if timeout is not None:
            try:
                await asyncio.wait_for(event.wait(), timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Timeout waiting for task {task_id}")
        else:
            await event.wait()
            
        return self._tasks_registry[task_id]

    async def wait_all(self, timeout: Optional[float] = None) -> List[CalculationTask]:
        """Blocks until all currently queued or running tasks finish."""
        # Get snapshots of the current task IDs
        pending_ids = [t.id for t in self._tasks_registry.values() if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)]
        if not pending_ids:
            return self.get_all_tasks()

        events = [self._completed_events[tid].wait() for tid in pending_ids]
        if timeout is not None:
            try:
                await asyncio.wait_for(asyncio.gather(*events), timeout)
            except asyncio.TimeoutError:
                pass
        else:
            await asyncio.gather(*events)
            
        return self.get_all_tasks()

    async def _worker_loop(self, worker_id: int):
        """Internal worker loop that consumes tasks from the queue."""
        while self.active:
            try:
                # Wait for next task
                task = await self._queue.get()
            except asyncio.CancelledError:
                break

            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            
            # Execute math calculation via middleware pipeline
            context = CalculationContext(task.expression, task.variables)
            
            try:
                # Core evaluation wrapper
                async def run_pipeline():
                    return await self.pipeline.execute(context, self.core_evaluator)
                
                await run_pipeline()
                
                task.completed_at = time.time()
                task.duration_ms = context.execution_time_ms
                task.cached = context.metadata.get("cached", False)
                
                if context.error:
                    task.status = TaskStatus.FAILED
                    task.error = f"{type(context.error).__name__}: {str(context.error)}"
                    self.failed_count += 1
                else:
                    task.status = TaskStatus.COMPLETED
                    task.result = context.result
                    self.processed_count += 1
                    self.total_latency_ms += task.duration_ms
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = f"WorkerException: {str(e)}"
                task.completed_at = time.time()
                self.failed_count += 1
            finally:
                self._queue.task_done()
                # Set completion event
                if task.id in self._completed_events:
                    self._completed_events[task.id].set()

    def get_metrics(self) -> Dict[str, Any]:
        """Retrieves performance and execution metrics."""
        avg_latency = 0.0
        if self.processed_count > 0:
            avg_latency = self.total_latency_ms / self.processed_count
            
        return {
            "num_workers": self.num_workers,
            "processed_tasks": self.processed_count,
            "failed_tasks": self.failed_count,
            "total_tasks_tracked": len(self._tasks_registry),
            "average_latency_ms": avg_latency,
            "active": self.active
        }
