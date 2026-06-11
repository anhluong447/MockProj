from src.services.calculator import CalculatorService, CalculationConfig

def helper_format(value: float) -> str:
    return f"Result: {value}"

class Application:
    def __init__(self):
        cfg = CalculationConfig()
        self.calc = CalculatorService(cfg)

    async def on_startup(self):
        print("Starting Mock Application...")
        self.run_demo()

    def run_demo(self):
        res1 = self.calc.add(10.5, 2.5)
        res2 = self.calc.multiply(3, 4)
        print(helper_format(res1))
        print(helper_format(res2))
