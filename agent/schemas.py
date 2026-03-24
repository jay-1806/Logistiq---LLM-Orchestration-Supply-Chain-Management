
from pydantic import BaseModel, Field
from typing import Any
from enum import Enum


# 1. TOOL CALL â€” What the planner asks for
class ToolCall(BaseModel):
    """
    A single step in the plan. The planner says:
    "For this step, use THIS tool with THESE arguments."

    Example:
    {
        "tool_name": "sql_query",
        "tool_args": {"query": "SELECT * FROM orders WHERE order_id = 'ORD-001'"},
        "reasoning": "Need to look up the order details first"
    }
    """
    tool_name: str = Field(
        description="Name of the tool to call (must match a registered tool)"
    )
    tool_args: dict = Field(
        description="Arguments to pass to the tool"
    )
    reasoning: str = Field(
        description="WHY this step is needed â€” helps with debugging and transparency"
    )


# 2. PLAN â€” The planner's full output
class Plan(BaseModel):
    """
    The planner's decomposition of a user query into ordered steps.

    Example:
    {
        "query": "Should we expedite order ORD-003?",
        "steps": [
            {"tool_name": "sql_query", "tool_args": {...}, "reasoning": "..."},
            {"tool_name": "doc_search", "tool_args": {...}, "reasoning": "..."},
            {"tool_name": "sql_query", "tool_args": {...}, "reasoning": "..."}
        ]
    }
    """
    query: str = Field(description="The original user question")
    steps: list[ToolCall] = Field(description="Ordered list of tool calls to execute")


# 3. STEP RESULT â€” What comes back from a tool
class StepResult(BaseModel):
    """
    The result of executing one step.

    We track success/failure so the executor can decide:
    - Success â†’ move to next step
    - Failure â†’ retry, skip, or abort
    """
    step_index: int = Field(description="Which step number this is (0-indexed)")
    tool_name: str = Field(description="Which tool was called")
    output: Any = Field(description="The tool's output (could be string, dict, list)")
    success: bool = Field(description="Did the tool call succeed?")
    error: str | None = Field(
        default=None,
        description="Error message if the tool call failed"
    )


class StructuredAnswer(BaseModel):
    """Normalized response schema for consistent enterprise outputs."""
    summary: str = Field(description="Short direct answer to user question")
    key_findings: list[str] = Field(default_factory=list, description="Evidence-backed findings")
    recommendations: list[str] = Field(default_factory=list, description="Actionable next steps")
    confidence: str = Field(default="medium", description="low | medium | high")


# 4. AGENT RESPONSE â€” The final answer
class AgentResponse(BaseModel):
    """
    The complete response sent back to the user.

    Includes the answer AND the "decision trail" â€” every step that was taken.
    This transparency is critical for enterprise use (auditability).
    """
    query: str = Field(description="Original user question")
    answer: str = Field(description="Final natural-language answer")
    plan: Plan = Field(description="The plan that was executed")
    step_results: list[StepResult] = Field(description="Results from each step")
    structured_answer: StructuredAnswer | None = Field(
        default=None,
        description="Normalized response payload for downstream systems"
    )
    total_tokens: int = Field(default=0, description="Total tokens used")
    total_cost: float = Field(default=0.0, description="Estimated total cost in USD")


# 5. USER ROLE â€” For role-based access control
class UserRole(str, Enum):
    """
    Different roles have access to different tools.

    VIEWER   â†’ can only search documents (read-only)
    ANALYST  â†’ can query databases + search docs
    MANAGER  â†’ full access including write operations
    """
    VIEWER = "viewer"
    ANALYST = "analyst"
    MANAGER = "manager"

