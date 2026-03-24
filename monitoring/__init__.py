
import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (as of March 2026)
# Gemini Flash is free for limited use, but we track as if it costs
# so the system is ready for paid models
MODEL_PRICING = {
    "gemini-2.0-flash": {"input": 0.0, "output": 0.0},      # Free tier
    "gemini-1.5-pro": {"input": 3.50, "output": 10.50},      # Per 1M tokens
    "gpt-4o": {"input": 2.50, "output": 10.00},              # For reference
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},          # For reference
}


@dataclass
class QueryCostRecord:
    """Cost breakdown for a single agent query."""
    timestamp: str
    query: str
    model: str
    planner_tokens: int = 0
    executor_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class CostTracker:
    """
    Tracks token usage and estimated costs across all queries.

    Usage:
        tracker = CostTracker()
        tracker.log_usage("gemini-2.0-flash", input_tokens=150, output_tokens=200, query="...")
        print(tracker.get_summary())
    """

    def __init__(self):
        self.records: list[QueryCostRecord] = []
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_cost: float = 0.0

    def log_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        query: str = "",
    ) -> QueryCostRecord:
        """
        Log token usage for a query.

        Args:
            model: Which model was used
            input_tokens: Tokens in the prompt
            output_tokens: Tokens in the response
            query: The user query (for reference)

        Returns:
            The cost record
        """
        total_tokens = input_tokens + output_tokens

        # Calculate cost
        pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
        cost = (input_tokens * pricing["input"] / 1_000_000 +
                output_tokens * pricing["output"] / 1_000_000)

        record = QueryCostRecord(
            timestamp=datetime.now().isoformat(),
            query=query[:100],  # Truncate for storage
            model=model,
            total_tokens=total_tokens,
            estimated_cost_usd=round(cost, 6),
        )

        self.records.append(record)
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost

        logger.info(
            f"Tokens: {total_tokens} (in:{input_tokens}, out:{output_tokens}) | "
            f"Cost: ${cost:.6f} | Model: {model}"
        )

        return record

    def get_summary(self) -> dict:
        """Get aggregate cost summary."""
        return {
            "total_queries": len(self.records),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "avg_tokens_per_query": (
                (self.total_input_tokens + self.total_output_tokens) // max(len(self.records), 1)
            ),
        }

