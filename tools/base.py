
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any
from agent.schemas import UserRole


class BaseTool(ABC):
    """
    Abstract base class for all tools in the platform.

    Every tool MUST:
    1. Have a unique name (used by planner to reference it)
    2. Have a description (the planner reads this to decide when to use it)
    3. Define its parameters schema (what arguments it accepts)
    4. Declare what role is needed to use it
    5. Implement execute() â€” the actual work

    Subclasses just implement execute() and set the class attributes.
    """

    # --- These are set by each subclass ---
    name: str = ""
    description: str = ""
    required_role: UserRole = UserRole.ANALYST
    args_model: type[BaseModel] | None = None

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Run the tool with the given arguments.

        Returns whatever the tool produces â€” could be:
        - A string (search results)
        - A list of dicts (SQL rows)
        - A dict (API response)

        Raises:
            Exception: If the tool call fails for any reason
        """
        pass

    def validate_args(self, raw_args: dict | None) -> dict:
        """Validate and normalize tool arguments using the declared args model."""
        if self.args_model is None:
            return raw_args or {}

        model = self.args_model.model_validate(raw_args or {})
        return model.model_dump()

    def get_input_schema(self) -> dict:
        """Return JSON schema for MCP-style tool discovery."""
        if self.args_model is None:
            return {
                "type": "object",
                "properties": {},
                "additionalProperties": True,
            }
        return self.args_model.model_json_schema()

    def get_mcp_spec(self) -> dict:
        """Return a structured tool specification similar to MCP tool manifests."""
        return {
            "name": self.name,
            "description": self.description,
            "required_role": self.required_role.value,
            "input_schema": self.get_input_schema(),
        }

    def get_description_for_planner(self) -> str:
        """
        Return a human-readable description for the planner's system prompt.

        The planner uses this to understand:
        - What this tool does
        - When to use it
        - What arguments it needs

        Example output:
            Tool: sql_query
            Description: Execute SQL queries against the supply chain database.
            Arguments: query (str) - The SQL query to execute
        """
        return (
            f"Tool: {self.name}\n"
            f"Description: {self.description}\n"
            f"Required Role: {self.required_role.value}\n"
            f"Input Schema: {self.get_input_schema()}"
        )

