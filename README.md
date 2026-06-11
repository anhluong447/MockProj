# Enterprise Math Engine (EME) 🧮🤖

An advanced, asynchronous mathematical computation engine built with a custom Tokenizer, Abstract Syntax Tree (AST) expression parser, execution middleware pipelines, and concurrent background worker task queues.

---

## 🌟 Key Features

1. **AST Math Expression Parser**:
   - Tokenizes and parses expressions using a custom **Recursive Descent** parser.
   - Supports infix arithmetic (`+`, `-`, `*`, `/`, `^`), unary operators, parenthesis nesting, and user variables.
   - Built-in mathematical functions (`sin`, `cos`, `tan`, `sqrt`, `log` with custom bases, `exp`, `abs`).

2. **Calculation Middleware Pipeline**:
   - Uses an **Onion Pattern** pipeline structure (similar to Koa/FastAPI middleware).
   - **`LoggingMiddleware`**: Full telemetry tracking of calculation parameters, errors, and execution timings.
   - **`CachingMiddleware`**: Efficient LRU/FIFO calculation caching to optimize redundant complex calculations.
   - **`ValidationMiddleware`**: Defends against overflow/underflow, expression bloating, and domain errors (e.g. division by zero, square root of negative numbers).
   - **`LatencySimulationMiddleware`**: Configurable latency simulator for performance staging.

3. **Asynchronous Background Task Queue**:
   - Concurrent worker pool executing calculation tasks in the background.
   - Precise task status registry (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`).
   - Thread-safe synchronization events (`wait_for_task`, `wait_all`) and detailed telemetry reporting.

---

## 📂 Architecture Layout

```
MockProj/
├── src/
│   ├── core/
│   │   ├── base.py              # Base service interface
│   │   ├── expression_parser.py # Lexer, AST nodes, and Parser
│   │   └── middleware.py        # Pipeline orchestrator & middlewares
│   ├── services/
│   │   ├── calculator.py        # Calculator service integration
│   │   └── task_queue.py        # Background task queue & worker pool
│   └── app.py                   # Demo runner & entry point
├── tests/
│   └── test_math_engine.py      # Automated unit test suite
└── README.md                    # Project documentation
```

---

## 🚀 Quick Start

### 1. Setup & Activate Environment
Ensure you have a Python environment configured:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Run the Demo Application
Execute the pipeline demonstration and worker task queue:
```powershell
python -m src.app
```

### 3. Run Unit Tests
Run the comprehensive test suite:
```powershell
python -m unittest tests/test_math_engine.py
```

---

## 📊 Sample Output & Telemetry Report

```
============================================================
      ENTERPRISE MATHEMATICAL CALCULATION ENGINE STARTED      
============================================================

--- [Step 1] Running Legacy Arithmetic Demo ---
Result: 13.0
Result: 12

--- [Step 2] Complex Expression Evaluation Demo ---
Evaluating formula: 'sin(x) * 2 + sqrt(y) ^ 2' where variables = {'x': 1.570796, 'y': 9.0}
Sync result (no middlewares): 11.0

--- [Step 3] Middleware & Caching Pipeline Demo ---
First execution (cold cache)...
Result 1: 11.0 (Cached: False) - Time: 81.67 ms
Second execution (hot cache)...
Result 2: 11.0 (Cached: True) - Time: 0.09 ms

--- [Step 4] Pipeline Security & Validation Demo ---
Error handling A ('10 / (5 - 5)'): error=Division by zero in formula evaluation.
Error handling B ('10 ^ 20'): error=Calculation result 1e+20 exceeds the safety limit of 1000000000000000.0.

--- [Step 5] Asynchronous Task Queue & Worker Pool Demo ---
[TaskQueueService] Started 3 background workers.
Submitting 6 tasks to the Queue...
Submitted task: e13547cc... -> 'log(100, 10) + abs(-5)'
Submitted task: 9d6216dd... -> 'x * 2.5'
Submitted task: 0302d905... -> 'sin(pi) + cos(pi)'
...
All tasks processed in 166.75 ms
```
