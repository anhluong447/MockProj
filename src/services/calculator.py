from dataclasses import dataclass, field
from src.core.base import BaseService

@dataclass
class CalculationConfig:
    precision: int = 4
    use_gpu: bool = False
    allowed_operations: list[str] = field(default_factory=lambda: ["add", "sub", "mul"])

class CalculatorService(BaseService):
    """Service for basic mathematical operations."""
    def __init__(self, config: CalculationConfig):
        super().__init__()
        self.config = config
        self.ops_count = 0

    def add(self, a: float, b: float) -> float:
        self.ops_count += 1
        return a + b

    def multiply(self, a: float, b: float) -> float:
        self.ops_count += 1
        return a * b
