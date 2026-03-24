
import logging
import math
from typing import Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, model_validator
from tools.base import BaseTool
from agent.schemas import UserRole

logger = logging.getLogger(__name__)

# Safe math functions available in expressions
SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "int": int,
    "float": float,
    "math": math,
}


class CalculatorTool(BaseTool):
    """
    Performs mathematical calculations and date arithmetic.

    For when the agent needs to compute values like:
    - Total order value: 500 * 89.99
    - Days remaining: days between today and ship-by date
    - Inventory coverage: quantity_on_hand / daily_demand
    """

    name = "calculator"
    description = (
        "Perform mathematical calculations. Use Python math expressions. "
        "Examples: '500 * 89.99', 'round(1000 / 7, 2)', 'max(10, 20, 30)'. "
        "Also supports date calculations: provide 'days_between' with "
        "'date1' and 'date2' in YYYY-MM-DD format. "
        "Arguments: expression (str) - A Python math expression to evaluate. "
        "OR date1 (str) + date2 (str) for date difference calculation."
    )
    required_role = UserRole.VIEWER  # Everyone can do math

    class Args(BaseModel):
        expression: str = Field(default="", description="Python math expression")
        date1: str = Field(default="", description="First date in YYYY-MM-DD")
        date2: str = Field(default="", description="Second date in YYYY-MM-DD")

        @model_validator(mode="after")
        def validate_mode(self):
            has_expression = bool(self.expression.strip())
            has_dates = bool(self.date1.strip() and self.date2.strip())
            if not has_expression and not has_dates:
                raise ValueError("Provide either expression, or both date1 and date2")
            return self

    args_model = Args

    def execute(self, expression: str = "", date1: str = "", date2: str = "", **kwargs) -> Any:
        """
        Evaluate a math expression or calculate days between dates.

        Args:
            expression: Python math expression (e.g., "500 * 89.99")
            date1: First date in YYYY-MM-DD format
            date2: Second date in YYYY-MM-DD format

        Returns:
            The calculated result
        """
        # --- Date calculation mode ---
        if date1 and date2:
            return self._days_between(date1, date2)

        if not expression:
            return "Error: No expression provided."

        # --- Safety check ---
        if len(expression) > 500:
            return "Error: Expression too long (max 500 characters)."

        # Block dangerous operations
        dangerous = ["import", "open", "exec", "eval", "__", "os.", "sys."]
        for keyword in dangerous:
            if keyword in expression.lower():
                return f"Error: '{keyword}' is not allowed in expressions."

        logger.info(f"Calculating: {expression}")

        try:
            # Evaluate with only safe math functions available
            result = eval(expression, {"__builtins__": {}}, SAFE_FUNCTIONS)
            logger.info(f"Result: {result}")
            return result
        except Exception as e:
            error_msg = f"Calculation error: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _days_between(self, date1: str, date2: str) -> str:
        """Calculate the number of days between two dates."""
        try:
            d1 = datetime.strptime(date1, "%Y-%m-%d")
            d2 = datetime.strptime(date2, "%Y-%m-%d")
            delta = (d2 - d1).days
            return f"{abs(delta)} days ({'d2 is later' if delta >= 0 else 'd1 is later'})"
        except ValueError as e:
            return f"Date parsing error: {str(e)}. Use YYYY-MM-DD format."

