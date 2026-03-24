
import logging
from typing import Optional
from tools.base import BaseTool
from agent.schemas import UserRole

logger = logging.getLogger(__name__)

# Role hierarchy â€” higher number = more access
ROLE_HIERARCHY = {
    UserRole.VIEWER: 1,
    UserRole.ANALYST: 2,
    UserRole.MANAGER: 3,
}


class ToolRegistry:
    """
    Central registry for all tools with role-based access control.

    Think of this as the "HR department" of the tool system:
    - It knows who everyone is (registration)
    - It controls who can do what (access control)
    - It provides a directory (tool descriptions for the planner)
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """
        Register a tool so the system knows it exists.

        Args:
            tool: An instance of a BaseTool subclass

        This is called at startup â€” we register all tools before
        the agent starts accepting queries.
        """
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered â€” overwriting")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} (requires: {tool.required_role.value})")

    def get_tool(self, name: str, user_role: UserRole) -> Optional[BaseTool]:
        """
        Get a tool by name, checking role-based access.

        Args:
            name: The tool name (as referenced in the Plan)
            user_role: The current user's role

        Returns:
            The tool if found AND the user has access, else None

        WHY WE CHECK ACCESS HERE (not in the executor):
        - Single point of enforcement â€” no matter how you access a tool,
          the permission check happens
        - The executor doesn't need to know about roles at all
        """
        tool = self._tools.get(name)

        if tool is None:
            logger.warning(f"Tool '{name}' not found in registry")
            return None

        # Check role hierarchy: user's role must be >= tool's required role
        user_level = ROLE_HIERARCHY.get(user_role, 0)
        required_level = ROLE_HIERARCHY.get(tool.required_role, 99)

        if user_level < required_level:
            logger.warning(
                f"Access denied: role '{user_role.value}' cannot use tool '{name}' "
                f"(requires '{tool.required_role.value}')"
            )
            return None

        return tool

    def get_all_descriptions(self, user_role: UserRole) -> str:
        """
        Get descriptions of all tools the user has access to.

        This is passed to the Planner so it knows what tools are available.
        The planner will only plan steps using tools the user can actually access.

        Args:
            user_role: Filter tools by this role

        Returns:
            Formatted string describing all accessible tools
        """
        descriptions = []
        user_level = ROLE_HIERARCHY.get(user_role, 0)

        for tool in self._tools.values():
            required_level = ROLE_HIERARCHY.get(tool.required_role, 99)
            if user_level >= required_level:
                descriptions.append(tool.get_description_for_planner())

        return "\n\n".join(descriptions) if descriptions else "No tools available."

    def list_tools(self) -> list[str]:
        """Return names of all registered tools (for debugging)."""
        return list(self._tools.keys())

    def get_mcp_tool_specs(self, user_role: UserRole) -> list[dict]:
        """Return structured tool specs for all tools available to a role."""
        specs = []
        user_level = ROLE_HIERARCHY.get(user_role, 0)
        for tool in self._tools.values():
            required_level = ROLE_HIERARCHY.get(tool.required_role, 99)
            if user_level >= required_level:
                specs.append(tool.get_mcp_spec())
        return specs

