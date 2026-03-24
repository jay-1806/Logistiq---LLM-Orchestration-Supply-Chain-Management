
import json
import logging
from pydantic import ValidationError
from langchain_groq import ChatGroq
from config.settings import settings
from agent.schemas import Plan, StepResult, AgentResponse, StructuredAnswer, UserRole
from agent.memory import ConversationMemory
from tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


# The synthesizer prompt â€” used to generate the final answer from all collected data
SYNTHESIZER_PROMPT = """You are a helpful supply chain operations assistant.

Based on the user's question and the data gathered from various tools, 
provide a clear, actionable answer.

## Rules:
1. Be specific â€” use actual numbers, dates, and names from the data
2. If the data is insufficient, say what's missing
3. For recommendations, explain your reasoning step by step
4. Keep answers concise but complete
5. If no tool data was gathered (simple question), just answer directly

## Conversation History:
{conversation_history}

## Tool Results:
{tool_results}

## User Question:
{query}

Provide your answer:"""

SYNTHESIZER_JSON_PROMPT = """You are a helpful supply chain operations assistant.

Based on the user question and tool results, return ONLY valid JSON using this schema:
{{
    "summary": "short direct answer",
    "key_findings": ["fact 1", "fact 2"],
    "recommendations": ["action 1", "action 2"],
    "confidence": "low|medium|high"
}}

Rules:
1. Output valid JSON only, no markdown.
2. Use evidence from tool results.
3. If data is missing, mention that in key_findings.
4. Keep recommendations practical and specific.

Conversation History:
{conversation_history}

Tool Results:
{tool_results}

User Question:
{query}
"""


class Executor:
    """
    Executes a Plan by running each tool call in sequence and synthesizing results.

    Think of this as the "developer" who receives a task list from the project
    manager (Planner) and executes each task one by one.
    """

    def __init__(self, tool_registry: ToolRegistry, memory: ConversationMemory):
        """
        Args:
            tool_registry: Registry containing all available tools + access control
            memory: Conversation history for context
        """
        self.tool_registry = tool_registry
        self.memory = memory

        # LLM for final answer synthesis
        self.llm = ChatGroq(
            model=settings.llm_model_name,
            groq_api_key=settings.groq_api_key,
            temperature=0.3,
            # Slightly higher temperature for synthesis â€” we want natural language
            # but still grounded in the data we gathered
        )

    def execute_plan(self, plan: Plan, user_role: UserRole = UserRole.ANALYST) -> AgentResponse:
        """
        Execute all steps in a plan and return the final response.

        This is the CORE LOOP of the entire agent. Here's what happens:

        1. For each step in the plan:
           - Look up the tool from the registry
           - Check if the user's role has access
           - Call the tool
           - Record the result
        2. After all steps: send everything to the LLM for a final answer

        Args:
            plan: The Plan to execute (from the Planner)
            user_role: The current user's role (for access control)

        Returns:
            Complete AgentResponse with answer + decision trail
        """
        step_results: list[StepResult] = []

        for i, step in enumerate(plan.steps):
            logger.info(f"Executing step {i + 1}/{len(plan.steps)}: {step.tool_name}")
            logger.info(f"  Reasoning: {step.reasoning}")

            # --- Step 1: Get the tool from registry ---
            tool = self.tool_registry.get_tool(step.tool_name, user_role)

            if tool is None:
                # Tool not found or user doesn't have access
                result = StepResult(
                    step_index=i,
                    tool_name=step.tool_name,
                    output=None,
                    success=False,
                    error=f"Tool '{step.tool_name}' not found or access denied for role '{user_role.value}'"
                )
                logger.warning(f"  âŒ {result.error}")
            else:
                # --- Step 2: Execute the tool ---
                try:
                    validated_args = tool.validate_args(step.tool_args)
                    output = tool.execute(**validated_args)
                    result = StepResult(
                        step_index=i,
                        tool_name=step.tool_name,
                        output=output,
                        success=True,
                    )
                    logger.info(f"  âœ… Tool returned successfully")
                except Exception as e:
                    result = StepResult(
                        step_index=i,
                        tool_name=step.tool_name,
                        output=None,
                        success=False,
                        error=str(e),
                    )
                    logger.error(f"  âŒ Tool failed: {e}")

            step_results.append(result)

        answer, structured = self._synthesize_answer(plan.query, step_results)

        response = AgentResponse(
            query=plan.query,
            answer=answer,
            plan=plan,
            step_results=step_results,
            structured_answer=structured,
        )

        return response

    def _synthesize_answer(self, query: str, step_results: list[StepResult]) -> tuple[str, StructuredAnswer | None]:
        """
        Given the query and all tool results, generate a natural-language answer.

        WHY THIS IS SEPARATE FROM EXECUTION:
        - The tools return raw data (SQL rows, document chunks, etc.)
        - The user wants a HUMAN-READABLE answer, not raw data
        - This step bridges the gap: raw data â†’ clear, actionable answer

        Think of this as writing the "executive summary" after gathering all the research.
        """
        # Format tool results into readable text
        if step_results:
            results_text = ""
            for result in step_results:
                status = "âœ… Success" if result.success else "âŒ Failed"
                results_text += f"\n### Step {result.step_index + 1}: {result.tool_name} ({status})\n"
                if result.success:
                    results_text += f"Output: {result.output}\n"
                else:
                    results_text += f"Error: {result.error}\n"
        else:
            results_text = "No tools were called â€” this is a simple question."

        # First try strict structured output for consistency.
        json_prompt = SYNTHESIZER_JSON_PROMPT.format(
            conversation_history=self.memory.get_history_string(),
            tool_results=results_text,
            query=query,
        )
        messages = [("human", json_prompt)]
        response = self.llm.invoke(messages)

        structured = self._parse_structured_answer(response.content)
        if structured is not None:
            return self._render_structured_answer(structured), structured

        # Fallback to free-form synthesis if JSON parsing fails.
        prompt = SYNTHESIZER_PROMPT.format(
            conversation_history=self.memory.get_history_string(),
            tool_results=results_text,
            query=query,
        )

        # Call the LLM for the fallback final answer
        messages = [("human", prompt)]
        response = self.llm.invoke(messages)

        return response.content, None

    def _parse_structured_answer(self, raw_output: str) -> StructuredAnswer | None:
        """Parse model JSON output into StructuredAnswer with tolerant fence cleanup."""
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            start = 0
            end = len(lines)
            for i, line in enumerate(lines):
                if line.strip().startswith("```"):
                    start = i + 1
                    break
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip().startswith("```"):
                    end = i
                    break
            cleaned = "\n".join(lines[start:end]).strip()

        try:
            data = json.loads(cleaned)
            return StructuredAnswer.model_validate(data)
        except (json.JSONDecodeError, ValidationError, TypeError):
            logger.warning("Structured answer parse failed; using fallback free-form answer.")
            return None

    def _render_structured_answer(self, structured: StructuredAnswer) -> str:
        """Render structured payload into stable human-readable text."""
        lines = [structured.summary.strip()]
        if structured.key_findings:
            lines.append("\nKey findings:")
            lines.extend([f"- {item}" for item in structured.key_findings])
        if structured.recommendations:
            lines.append("\nRecommendations:")
            lines.extend([f"- {item}" for item in structured.recommendations])
        lines.append(f"\nConfidence: {structured.confidence}")
        return "\n".join(lines)

