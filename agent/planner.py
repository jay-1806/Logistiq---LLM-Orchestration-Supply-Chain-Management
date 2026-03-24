
import json
import logging
from langchain_groq import ChatGroq
from config.settings import settings
from agent.schemas import Plan, ToolCall

logger = logging.getLogger(__name__)


# THE PLANNING PROMPT
# This is the most important piece of prompt engineering in the project.
# Every word matters. Let's break down why each section exists:

PLANNER_SYSTEM_PROMPT = """You are a planning agent for a supply chain operations platform.

Your job is to decompose a user's question into a sequence of tool calls that, 
when executed in order, will gather all the information needed to answer the question.

## Available Tools

{tools_description}

## Rules

1. Output ONLY valid JSON matching this exact schema:
{{
    "query": "the original user question",
    "steps": [
        {{
            "tool_name": "name of the tool to call",
            "tool_args": {{"arg_name": "arg_value"}},
            "reasoning": "why this step is needed"
        }}
    ]
}}

2. Each step should use ONE tool. Order steps logically â€” data gathering first, 
   then analysis.

3. For SQL queries, write valid SQLite SQL. The database has these tables:
   - orders(order_id, customer, product, quantity, unit_price, status, priority, created_at, ship_by, notes)
   - inventory(product, warehouse, quantity_on_hand, reorder_point, last_updated)
   - shipments(shipment_id, order_id, carrier, tracking_number, status, shipped_at, estimated_delivery)
   - quality_holds(hold_id, unit_serial_number, product, reason, severity, status, created_at, resolved_at, resolution_notes)

4. For document searches, provide a clear search query that captures the intent.

5. Keep plans concise â€” use the minimum number of steps needed.

6. If the question is simple (e.g., "hello"), return zero steps and just answer directly.

## Conversation History
{conversation_history}
"""


class Planner:
    """
    Decomposes user queries into executable plans.

    Think of this as the "project manager" â€” it reads the requirement (user query),
    looks at available resources (tools), and creates a task list (Plan).
    """

    def __init__(self):
        """Initialize the LLM used for planning."""
        # We use Groq for planning â€” fast inference with free tier availability
        self.llm = ChatGroq(
            model=settings.llm_model_name,
            groq_api_key=settings.groq_api_key,
            temperature=settings.llm_temperature,
            # temperature=0 â†’ deterministic output
            # For a planner, we want CONSISTENT plans, not creative ones
        )

    def create_plan(
        self,
        query: str,
        tools_description: str,
        conversation_history: str = "No previous conversation."
    ) -> Plan:
        """
        Generate an execution plan for the given query.

        Args:
            query: The user's question
            tools_description: Human-readable list of available tools and their capabilities
            conversation_history: Recent conversation for context

        Returns:
            A validated Plan object with ordered steps

        Raises:
            ValueError: If the LLM output can't be parsed into a valid Plan
        """
        # 1. Build the prompt
        system_prompt = PLANNER_SYSTEM_PROMPT.format(
            tools_description=tools_description,
            conversation_history=conversation_history,
        )

        # 2. Call the LLM
        logger.info(f"Planning for query: {query}")
        messages = [
            ("system", system_prompt),
            ("human", f"Create a plan for this question: {query}"),
        ]
        response = self.llm.invoke(messages)
        raw_output = response.content
        logger.debug(f"Raw planner output: {raw_output}")

        # 3. Parse the JSON output
        plan = self._parse_plan(raw_output, query)
        logger.info(f"Plan created with {len(plan.steps)} steps")
        return plan

    def _parse_plan(self, raw_output: str, original_query: str) -> Plan:
        """Parse model output into a validated Plan object."""
        # Strip markdown code fences if present
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            # Remove ```json and closing ```
            lines = cleaned.split("\n")
            # Find first and last lines that are ```
            start = 0
            end = len(lines) - 1
            for i, line in enumerate(lines):
                if line.strip().startswith("```"):
                    start = i + 1
                    break
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() == "```":
                    end = i
                    break
            cleaned = "\n".join(lines[start:end])

        try:
            data = json.loads(cleaned)
            plan = Plan(**data)
            return plan
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse plan: {e}. Returning empty plan.")
            return Plan(query=original_query, steps=[])

