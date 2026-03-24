# Logistiq AI Stakeholder Guide

## 1) What This Project Is
Logistiq AI is an AI assistant for supply chain operations.
It answers questions by:
- planning what steps are needed,
- using trusted tools (database, policy docs, calculator),
- returning clear answers with evidence.

This is not a simple chatbot. It is a tool-orchestrated agent with role-based access control and explainable outputs.

## 2) Why It Matters (Business Value)
- Faster decisions for operations teams.
- One interface for both SQL data and policy documents.
- Better trust through transparent decision trail and source references.
- Role-based control for safer enterprise usage.

## 3) How The System Works (Simple Workflow)
1. User asks a question in the Streamlit UI.
2. Planner creates a step-by-step plan.
3. Executor runs those steps using tools.
4. Tool results are combined into a structured final answer.
5. UI shows:
   - Result card,
   - key findings,
   - recommendations,
   - confidence,
   - decision trail,
   - result table (if SQL rows are returned),
   - source citations (if docs were used).

## 4) End-to-End Architecture
User Query -> Planner (Groq) -> Plan -> Executor -> Tools -> Final Answer

Tools used by Executor:
- SQL Tool (SQLite read-only)
- RAG Tool (Document search)
- Calculator Tool (math/date)

## 5) Main Modules And Their Responsibilities

### Agent Layer
- agent/orchestrator.py
  - Wires everything together.
  - Initializes database, retriever, tools, planner, executor.
- agent/planner.py
  - Converts user question into a tool plan.
- agent/executor.py
  - Executes each planned tool step.
  - Builds structured answer: summary, findings, recommendations, confidence.
- agent/memory.py
  - Maintains conversation context.
- agent/schemas.py
  - Defines strict data contracts for reliability.

### Tools Layer (MCP-style)
- tools/base.py
  - Standard tool interface.
  - Input schema and arg validation support.
- tools/registry.py
  - Registers tools and enforces role permissions.
- tools/sql_tool.py
  - Read-only SQL query execution.
- tools/rag_tool.py
  - Searches internal documents.
- tools/calculator_tool.py
  - Performs math/date calculations.

### RAG Layer
- rag/loader.py
  - Loads and chunks docs.
- rag/vectorstore.py
  - Embedding and semantic search via ChromaDB.
- rag/retriever.py
  - Hybrid retrieval (vector + BM25 keyword search).

### Data Layer
- data/setup_database.py
  - Creates baseline schema and sample data.
- data/load_enterprise_dataset.py
  - Loads larger enterprise-style dataset (Olist) into same schema.

### UI Layer
- ui/app.py
  - Chat UI, role switching, RBAC display, guided empty state.
  - Result card rendering, table rendering, RAG source display.

### Config + Monitoring
- config/settings.py
  - Validated environment config (.env).
- evaluation/cost_tracker.py
  - Token/cost tracking summary.

## 6) Features Implemented
- Planner-Executor architecture.
- Role-based access control (viewer, analyst, manager).
- PIN-protected role elevation option.
- Structured outputs for consistent responses.
- Decision trail for transparency.
- SQL table rendering in UI.
- RAG source references with snippets and relevance reason.
- Guided empty state (GPT-style) for first interaction.
- Enterprise dataset mode for large-scale demo.

## 7) Role-Based Access (RBAC)
- Viewer:
  - Document search only.
- Analyst:
  - Database + document search.
- Manager:
  - Full access to all registered tools.

Why this is important:
- Prevents accidental data misuse.
- Makes demos look enterprise-ready.

## 8) Tech Stack And Why It Is Used

| Area | Tech | Why |
|---|---|---|
| UI | Streamlit | Fast internal app development, easy demos |
| LLM | Groq via LangChain | Fast model inference and easy integration |
| Validation | Pydantic + pydantic-settings | Strict schemas and safer config handling |
| SQL data | SQLite | Simple, reliable relational backend for demos |
| Document retrieval | ChromaDB + sentence-transformers | Local semantic search over internal docs |
| Hybrid search | rank-bm25 | Better keyword matching for IDs/terms |
| Observability | Cost tracker (and MLflow dependency) | Cost awareness and extensibility |

## 9) Example Workflow A (SQL Data Question)
Question: Show the 5 most recent orders.

Expected flow:
1. Planner selects sql_query.
2. SQL tool runs read-only SELECT query.
3. Executor synthesizes output.
4. UI displays:
   - verdict,
   - key findings,
   - recommendation,
   - confidence,
   - result table.

## 10) Example Workflow B (Policy Question with Sources)
Question: According to policy docs, what is the shipping SLA escalation timeline? Include sources.

Expected flow:
1. Planner selects doc_search.
2. RAG tool retrieves document chunks.
3. Executor synthesizes answer.
4. UI displays:
   - answer summary,
   - source document names,
   - short snippets,
   - relevance reason.

## 11) How To Use (Operational Steps)
1. Set environment values in .env (GROQ API key, optional role PIN).
2. Install dependencies from requirements.txt.
3. Initialize sample DB or load enterprise dataset.
4. Start Streamlit app.
5. Choose role and ask questions.
6. Review result card + decision trail + sources.

## 12) Enterprise Data Mode (Large Dataset)
To simulate enterprise scale, load Olist data into the same schema.

Recommended command from project root:
python -m data.load_enterprise_dataset --source-dir ./Olist_Ecommerce_Dataset --max-orders 100000

## 13) Known Gaps / Next Improvements
- Add user login (real identity-to-role mapping).
- Add production audit logs (query id, tool latency, role trace).
- Add automated evaluation for answer quality.
- Align cost tracker model pricing map to current Groq model set.

## 14) One-Page Summary For Stakeholders
Logistiq AI is an enterprise-style supply chain assistant that is:
- reliable (structured outputs),
- transparent (decision trail + source references),
- controlled (RBAC),
- scalable for demos (enterprise dataset mode),
- practical for operations teams.
