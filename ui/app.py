
import streamlit as st
import logging
import sys
import os
import re
from typing import Any

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.orchestrator import AgentOrchestrator
from agent.schemas import UserRole
from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")


# PAGE CONFIG
st.set_page_config(
    page_title="Logistiq AI - Supply Chain Copilot",
    page_icon=":factory:",
    layout="wide",
)


# CUSTOM STYLING
st.markdown("""
<style>
    /* Dark theme adjustments */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Step result cards */
    .step-card {
        background: #1a1d23;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        border-left: 3px solid #4CAF50;
    }
    .step-card.failed {
        border-left-color: #f44336;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #1a1d23, #2d3139);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }

    /* Assistant result card */
    .result-card {
        background: linear-gradient(180deg, #141a24, #101520);
        border: 1px solid #2b3445;
        border-radius: 12px;
        padding: 14px 16px;
        margin: 6px 0 12px 0;
    }
    .result-label {
        color: #9db0cf;
        font-size: 0.78rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .result-verdict {
        color: #e9edf7;
        font-size: 1.02rem;
        font-weight: 650;
        margin-bottom: 10px;
    }
    .status-chip {
        display: inline-block;
        border-radius: 999px;
        padding: 2px 10px;
        font-size: 0.78rem;
        font-weight: 650;
        margin-left: 8px;
        border: 1px solid transparent;
    }
    .status-success { background: #112b1c; color: #67e8a5; border-color: #245437; }
    .status-no-results { background: #2b2412; color: #fcd34d; border-color: #5b4b1f; }
    .status-partial { background: #2a2032; color: #d8b4fe; border-color: #4f2f60; }
    .status-failed { background: #31161b; color: #fda4af; border-color: #63323a; }

    .confidence-badge {
        display: inline-block;
        border-radius: 999px;
        padding: 2px 10px;
        font-size: 0.78rem;
        font-weight: 650;
        border: 1px solid transparent;
    }
    .conf-high { background: #112b1c; color: #67e8a5; border-color: #245437; }
    .conf-medium { background: #2b2412; color: #fcd34d; border-color: #5b4b1f; }
    .conf-low { background: #31161b; color: #fda4af; border-color: #63323a; }

    /* Sidebar user card */
    .user-card {
        background: linear-gradient(180deg, #1a2230, #121925);
        border: 1px solid #2f3a4f;
        border-radius: 12px;
        padding: 12px;
        margin: 8px 0 12px 0;
    }
    .user-card .label {
        color: #91a4c4;
        font-size: 0.76rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .user-card .value {
        color: #f3f6ff;
        font-size: 1rem;
        font-weight: 700;
        margin-top: 2px;
    }

    .perm-card {
        background: #141c29;
        border: 1px solid #2d3a52;
        border-radius: 10px;
        padding: 10px 12px;
        margin: 6px 0 10px 0;
        color: #d8e1f2;
        font-size: 0.92rem;
    }

    /* Empty state */
    .empty-wrap {
        background: linear-gradient(180deg, #121827, #0f1522);
        border: 1px solid #2a3550;
        border-radius: 14px;
        padding: 16px;
        margin: 10px 0 16px 0;
    }
    .empty-title {
        color: #eef3ff;
        font-size: 1.08rem;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .empty-sub {
        color: #a9bad8;
        font-size: 0.93rem;
        margin-bottom: 10px;
    }
    .cap-chip {
        display: inline-block;
        background: #17243a;
        border: 1px solid #2f486d;
        color: #d9e7ff;
        border-radius: 999px;
        padding: 4px 10px;
        margin: 4px 6px 4px 0;
        font-size: 0.82rem;
    }

    /* Source citation cards for RAG */
    .source-card {
        background: #121a28;
        border: 1px solid #2b3a53;
        border-radius: 10px;
        padding: 10px 12px;
        margin: 8px 0;
    }
    .source-title {
        color: #d8e6ff;
        font-weight: 650;
        margin-bottom: 4px;
    }
    .source-snippet {
        color: #b8c9e6;
        font-size: 0.9rem;
        margin-bottom: 6px;
    }
    .source-reason {
        color: #93a8cb;
        font-size: 0.82rem;
    }
</style>
""", unsafe_allow_html=True)


# INITIALIZE AGENT (cached so it only runs once)
@st.cache_resource
def get_agent():
    """
    Initialize the agent. Cached so it persists across re-runs.
    
    st.cache_resource means: run this ONCE, then reuse the result.
    Without this, the agent would re-initialize every time you type.
    """
    agent = AgentOrchestrator()
    agent.initialize()
    return agent


# SESSION STATE - Persistent across interactions
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_responses" not in st.session_state:
    st.session_state.agent_responses = []
if "current_role" not in st.session_state:
    st.session_state.current_role = "analyst"


def _is_empty_tool_output(output: Any) -> bool:
    """Best-effort check for empty tool outputs for status classification."""
    if output is None:
        return True
    if isinstance(output, str):
        normalized = output.strip().lower()
        return (
            normalized == ""
            or normalized.startswith("no results found")
            or normalized.startswith("no relevant documents found")
        )
    if isinstance(output, (list, tuple, set, dict)):
        return len(output) == 0
    return False


def _classify_response_status(response) -> str:
    """Return one of: success | no-results | partial | failed."""
    steps = response.step_results or []
    if not steps:
        return "success"

    success_steps = [s for s in steps if s.success]
    failed_steps = [s for s in steps if not s.success]

    if failed_steps and not success_steps:
        return "failed"
    if failed_steps and success_steps:
        return "partial"

    # All steps successful; inspect whether data came back.
    if all(_is_empty_tool_output(s.output) for s in success_steps):
        return "no-results"
    return "success"


def _build_result_sections(response) -> tuple[str, list[str], list[str], str]:
    """Build verdict/findings/recommendations/confidence with robust fallbacks."""
    status = _classify_response_status(response)
    structured = response.structured_answer

    findings = list(structured.key_findings) if structured else []
    recs = list(structured.recommendations) if structured else []

    if status == "failed":
        verdict = "Could not determine the result."
        findings = findings or [
            f"Tool step failed: {s.tool_name} - {s.error}" for s in response.step_results if not s.success
        ]
        recs = recs or [
            "Retry the query with a stricter read-only SQL instruction.",
            "Inspect the failed step in Decision Trail for exact error details.",
        ]
        confidence = "low"
    elif status == "partial":
        verdict = "Partial answer available."
        findings = findings or [
            "Some tool steps succeeded while others failed.",
            "See Decision Trail for failed step details.",
        ]
        recs = recs or [
            "Retry to complete failed steps.",
            "Use narrower query scope to reduce tool failures.",
        ]
        confidence = "medium"
    elif status == "no-results":
        verdict = "No matching records were found."
        findings = findings or ["All executed tools returned empty results."]
        recs = recs or [
            "Try a broader filter or wider date range.",
            "Verify source data freshness in the underlying tables.",
        ]
        confidence = "high"
    else:
        verdict = structured.summary if structured and structured.summary else response.answer.split("\n")[0].strip()
        findings = findings or ["Requested data was retrieved successfully."]
        recs = recs or ["Use Decision Trail to review tool-level evidence."]
        confidence = (structured.confidence if structured and structured.confidence else "medium").lower()

    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"

    return verdict, findings, recs, confidence


def _extract_tabular_rows(response) -> list[dict] | None:
    """Extract first tabular tool output (list of dict rows) for UI table rendering."""
    for step in response.step_results:
        if not step.success:
            continue
        output = step.output
        if isinstance(output, list) and output and all(isinstance(row, dict) for row in output):
            return output
    return None


def _relevance_reason(score: float) -> str:
    """Convert numeric relevance score into a simple confidence reason."""
    if score >= 0.75:
        return "High semantic match to your question"
    if score >= 0.5:
        return "Moderate semantic match; useful supporting context"
    return "Low semantic match; use as secondary context"


def _extract_rag_sources(response) -> list[dict]:
    """Parse doc_search output and return normalized source citations."""
    sources: list[dict] = []
    pattern = re.compile(
        r"---\s*Document Chunk\s*\d+\s*\(Source:\s*(.*?),\s*Relevance:\s*([0-9.]+)\)\s*---\s*\n(.*?)(?=\n\n---\s*Document Chunk|\Z)",
        re.DOTALL,
    )

    for step in response.step_results:
        if not step.success or step.tool_name != "doc_search" or not isinstance(step.output, str):
            continue
        for match in pattern.finditer(step.output):
            source = match.group(1).strip()
            score_raw = match.group(2).strip()
            content = " ".join(match.group(3).strip().split())
            try:
                score = float(score_raw)
            except ValueError:
                score = 0.0

            snippet = content[:220] + ("..." if len(content) > 220 else "")
            sources.append(
                {
                    "source": source,
                    "score": score,
                    "snippet": snippet,
                    "reason": _relevance_reason(score),
                }
            )

    # Deduplicate by source while keeping highest-score chunk first.
    sources = sorted(sources, key=lambda x: x["score"], reverse=True)
    unique: list[dict] = []
    seen = set()
    for item in sources:
        src = item["source"]
        if src in seen:
            continue
        seen.add(src)
        unique.append(item)
        if len(unique) >= 3:
            break
    return unique


def render_result_card(response):
    """Render assistant output in a single structured card."""
    status = _classify_response_status(response)
    verdict, findings, recs, confidence = _build_result_sections(response)

    status_label_map = {
        "success": "success",
        "no-results": "no results",
        "partial": "partial answer",
        "failed": "failed query",
    }

    st.markdown(
        f"""
        <div class="result-card">
            <div class="result-label">Result
                <span class="status-chip status-{status}">{status_label_map.get(status, status)}</span>
            </div>
            <div class="result-verdict">{verdict}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**Key findings**")
    for item in findings:
        st.markdown(f"- {item}")

    st.markdown("**Recommendations**")
    for item in recs:
        st.markdown(f"- {item}")

    st.markdown(
        f"**Confidence**  <span class='confidence-badge conf-{confidence}'>{confidence}</span>",
        unsafe_allow_html=True,
    )

    # Show table for SQL-like tabular outputs when available.
    table_rows = _extract_tabular_rows(response)
    if table_rows:
        st.markdown("**Result table**")
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

    # Show citations for document-based (RAG) answers when available.
    rag_sources = _extract_rag_sources(response)
    if rag_sources:
        source_names = [item["source"] for item in rag_sources]
        if len(source_names) == 1:
            st.markdown(f"**Based on** {source_names[0]}")
        else:
            st.markdown(f"**Based on** {', '.join(source_names[:-1])} and {source_names[-1]}")

        st.markdown("**Sources**")
        for item in rag_sources:
            st.markdown(
                f"""
                <div class="source-card">
                    <div class="source-title">{item['source']} (relevance: {item['score']:.2f})</div>
                    <div class="source-snippet">{item['snippet']}</div>
                    <div class="source-reason">Reason: {item['reason']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# SIDEBAR - Controls
with st.sidebar:
    st.markdown("## Logistiq AI Console")
    st.markdown("---")

    # Role selector with PIN protection for elevated roles.
    role_options = ["viewer", "analyst", "manager"]
    current_role = st.session_state.current_role
    if current_role not in role_options:
        current_role = "analyst"
        st.session_state.current_role = current_role

    if "role_selector" not in st.session_state:
        st.session_state.role_selector = current_role

    role_pin_required = (settings.role_change_pin or "").strip()

    selected_role = st.selectbox(
        "Select User Role",
        options=role_options,
        help="Role-based access control for tool permissions",
        key="role_selector",
    )

    elevated_roles = {"analyst", "manager"}
    role_change_requested = selected_role != current_role
    # Ask PIN only when selecting an elevated role.
    pin_needed = bool(role_pin_required and role_change_requested and selected_role in elevated_roles)

    if role_change_requested and not pin_needed:
        st.session_state.current_role = selected_role
        st.rerun()

    if pin_needed:
        st.warning("PIN required to change analyst/manager roles.")
        entered_pin = st.text_input(
            "Enter Role Change PIN",
            type="password",
            key="role_pin_input",
        )
        col_apply, col_cancel = st.columns(2)
        with col_apply:
            if st.button("Apply Role", use_container_width=True):
                if entered_pin == role_pin_required:
                    st.session_state.current_role = selected_role
                    st.rerun()
                else:
                    st.error("Invalid PIN. Role not changed.")
        with col_cancel:
            if st.button("Cancel", use_container_width=True):
                st.session_state.role_selector = current_role
                st.rerun()

    role = st.session_state.current_role
    user_role = UserRole(role)

    st.markdown(
        f"""
        <div class="user-card">
            <div class="label">Active User</div>
            <div class="value">USER: {role.upper()}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("---")

    # Show only current role permission.
    st.markdown("### Role Permissions")
    role_info = {
        "viewer": "Can search documents only",
        "analyst": "Can query database + search docs",
        "manager": "Full access to all tools",
    }
    st.markdown(
        f"<div class='perm-card'>{role_info[role]}</div>",
        unsafe_allow_html=True,
    )
    
    st.markdown("---")
    
    # Cost summary
    st.markdown("### Cost Tracker")
    try:
        agent = get_agent()
        summary = agent.cost_tracker.get_summary()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Queries", summary["total_queries"])
        with col2:
            st.metric("Tokens", summary["total_tokens"])
        st.metric("Est. Cost", f"${summary['total_cost_usd']:.4f}")
    except Exception:
        st.info("No queries yet")
    
    st.markdown("---")
    st.markdown("### Try These Queries")
    if role == "viewer":
        example_queries = [
            "What are the key points from the shipping SLA policy?",
            "Summarize the expedite policy in simple terms.",
            "What does the quality manual say about re-test decisions?",
            "According to policy docs, what is the shipping SLA escalation timeline? Include sources.",
        ]
    else:
        example_queries = [
            "Show the 5 most recent orders.",
            "How many orders are pending right now?",
            "List 5 customers with the highest order volume.",
            "Show 5 open quality holds with severity.",
            "What are the key points from the shipping SLA policy?",
            "According to policy docs, what is the shipping SLA escalation timeline? Include sources.",
        ]
    for q in example_queries:
        if st.button(q, key=f"example_{q}", use_container_width=True):
            st.session_state.pending_query = q
            st.rerun()

    st.markdown("---")

    # Clear chat is intentionally at the very bottom of the sidebar.
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent_responses = []
        agent = get_agent()
        agent.reset_conversation()
        st.rerun()


# MAIN AREA - Chat Interface
st.markdown("# Logistiq AI - Supply Chain Copilot")
st.markdown("*AI-powered assistant for supply chain operations. Ask about orders, inventory, shipments, quality, and policies.*")
st.markdown("---")

# GPT-style guided empty state (disappears once chat starts).
if not st.session_state.messages and not st.session_state.get("pending_query"):
    st.markdown(
        """
        <div class="empty-wrap">
            <div class="empty-title">What Logistiq AI Can Do</div>
            <div class="empty-sub">Start with a prompt below.</div>
            <span class="cap-chip">Order Tracking</span>
            <span class="cap-chip">Inventory Insights</span>
            <span class="cap-chip">Quality Hold Analysis</span>
            <span class="cap-chip">Policy Q&A with Sources</span>
            <span class="cap-chip">Role-Based Access Control</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**Try one of these prompts**")
    starter_prompts = [
        "Show the 5 most recent orders.",
        "How many orders are pending right now?",
        "Show 5 open quality holds with severity.",
        "According to policy docs, what is the shipping SLA escalation timeline? Include sources.",
    ]
    cols = st.columns(2)
    for idx, prompt in enumerate(starter_prompts):
        with cols[idx % 2]:
            if st.button(prompt, key=f"starter_{idx}", use_container_width=True):
                st.session_state.pending_query = prompt
                st.rerun()

    st.caption("Role-based access: viewer = policy/docs only, analyst = database + docs, manager = full access.")

# Display chat history
assistant_response_idx = 0
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and assistant_response_idx < len(st.session_state.agent_responses):
            response = st.session_state.agent_responses[assistant_response_idx]
            render_result_card(response)
            
            with st.expander("Decision Trail - See how the agent arrived at this answer"):
                # Show plan
                st.markdown("#### Plan")
                for j, step in enumerate(response.plan.steps):
                    st.markdown(f"**Step {j+1}:** `{step.tool_name}` - {step.reasoning}")
                
                if not response.plan.steps:
                    st.info("No tools needed - answered directly.")
                
                # Show step results
                st.markdown("#### Tool Results")
                for result in response.step_results:
                    status = "OK" if result.success else "FAIL"
                    st.markdown(f"**{status} {result.tool_name}**")
                    if result.success:
                        st.code(str(result.output)[:500], language="json")
                    else:
                        st.error(result.error)
            assistant_response_idx += 1
        else:
            st.markdown(message["content"])


# CHAT INPUT
# Check for pending query from sidebar examples
pending = st.session_state.pop("pending_query", None)
user_input = pending or st.chat_input("Ask about orders, inventory, shipping, quality...")

if user_input:
    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                agent = get_agent()
                response = agent.query(user_input, user_role)
                
                # Display answer card
                render_result_card(response)
                
                # Store response for decision trail
                st.session_state.agent_responses.append(response)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.answer,
                })
                
                # Show decision trail
                with st.expander("Decision Trail - See how the agent arrived at this answer"):
                    if response.structured_answer is not None:
                        st.markdown("#### Structured Output")
                        st.json(response.structured_answer.model_dump())

                    st.markdown("#### Plan")
                    for j, step in enumerate(response.plan.steps):
                        st.markdown(f"**Step {j+1}:** `{step.tool_name}` - {step.reasoning}")
                    
                    if not response.plan.steps:
                        st.info("No tools needed - answered directly.")
                    
                    st.markdown("#### Tool Results")
                    for result in response.step_results:
                        status = "OK" if result.success else "FAIL"
                        st.markdown(f"**{status} {result.tool_name}**")
                        if result.success:
                            st.code(str(result.output)[:500], language="json")
                        else:
                            st.error(result.error)
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.info("Make sure your .env file has a valid GROQ_API_KEY.")

