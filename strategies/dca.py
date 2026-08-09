"""📈 الفهد — استراتيجية DCA"""
from typing import Dict, List

class DCAStrategy:
    """Dollar Cost Averaging"""
    def __init__(self, config: Dict = None):
        self.config = config or {}
    
    def generate_plan(self, symbol: str, entry_price: float, total_budget: float) -> Dict:
        return {"type": "dca", "symbol": symbol, "entry": entry_price, "total_budget": total_budget}
