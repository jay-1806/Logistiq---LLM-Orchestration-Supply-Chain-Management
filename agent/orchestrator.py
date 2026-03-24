
import logging
import os
from agent.planner import Planner
from agent.executor import Executor
from agent.memory import ConversationMemory
from agent.schemas import AgentResponse, UserRole
from tools.registry import ToolRegistry
from tools.sql_tool import SQLTool
from tools.rag_tool import RAGTool
from tools.calculator_tool import CalculatorTool
from rag.loader import DocumentLoader
from rag.vectorstore import VectorStore
from rag.retriever import HybridRetriever
from evaluation.cost_tracker import CostTracker
from config.settings import settings

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    The main entry point for the agent system.

    This class:
    1. Initializes all components on startup
    2. Provides a simple query() method for the UI to call
    3. Manages the conversation lifecycle

    Usage:
        agent = AgentOrchestrator()
        agent.initialize()
        response = agent.query("What's the status of order ORD-001?")
        print(response.answer)
    """

    def __init__(self):
        self.planner: Planner | None = None
        self.executor: Executor | None = None
        self.memory = ConversationMemory(max_exchanges=10)
        self.tool_registry = ToolRegistry()
        self.cost_tracker = CostTracker()
        self.retriever: HybridRetriever | None = None
        self._initialized = False

    def initialize(self):
        """
        Set up all components. Call this once before querying.

        This is separated from __init__ because:
        1. It does heavy work (loading models, indexing docs)
        2. It might fail (missing API key, missing files)
        3. We want to control WHEN it happens (not at import time)
        """
        logger.info("=" * 60)
        logger.info("Initializing Agent Orchestrator")
        logger.info("=" * 60)

        # --- Step 1: Set up the database ---
        self._setup_database()

        # --- Step 2: Build RAG pipeline ---
        self._setup_rag()

        # --- Step 3: Register tools ---
        self._setup_tools()

        # --- Step 4: Create planner and executor ---
        self.planner = Planner()
        self.executor = Executor(
            tool_registry=self.tool_registry,
            memory=self.memory,
        )

        self._initialized = True
        logger.info("=" * 60)
        logger.info("Agent Orchestrator ready!")
        logger.info(f"Tools available: {self.tool_registry.list_tools()}")
        logger.info("=" * 60)

    def _setup_database(self):
        """Create the supply chain database if it doesn't exist."""
        if not os.path.exists(settings.database_path):
            logger.info("Database not found â€” creating with sample data...")
            from data.setup_database import create_database
            create_database(settings.database_path)
        else:
            logger.info(f"Database found at {settings.database_path}")

    def _setup_rag(self):
        """Build the full RAG pipeline: load â†’ chunk â†’ embed â†’ index."""
        # Load and chunk documents
        loader = DocumentLoader()
        chunks = loader.load_and_chunk()

        if not chunks:
            logger.warning("No documents found â€” RAG will not be available.")
            self.retriever = None
            return

        # Create vector store and index chunks
        vector_store = VectorStore()

        # Only re-index if the collection is empty
        if vector_store.collection.count() == 0:
            logger.info("Vector store is empty â€” indexing documents...")
            vector_store.add_chunks(chunks)
        else:
            logger.info(
                f"Vector store already has {vector_store.collection.count()} documents. "
                f"Skipping re-indexing. Use vector_store.reset() to re-index."
            )

        # Create hybrid retriever
        self.retriever = HybridRetriever(
            vector_store=vector_store,
            chunks=chunks,
            top_k=settings.top_k,
        )

    def _setup_tools(self):
        """Create and register all tools."""
        # SQL Tool â€” for database queries
        sql_tool = SQLTool()
        self.tool_registry.register(sql_tool)

        # RAG Tool â€” for document search
        rag_tool = RAGTool(retriever=self.retriever)
        self.tool_registry.register(rag_tool)

        # Calculator Tool â€” for math and date operations
        calc_tool = CalculatorTool()
        self.tool_registry.register(calc_tool)

        logger.info(f"Registered {len(self.tool_registry.list_tools())} tools")

    def query(
        self,
        user_query: str,
        user_role: UserRole = UserRole.ANALYST,
    ) -> AgentResponse:
        """
        Process a user query end-to-end.

        This is the MAIN METHOD â€” the UI calls this.

        Flow:
        1. Add user message to memory
        2. Planner creates a plan (list of tool calls)
        3. Executor runs the plan
        4. Add assistant response to memory
        5. Return the complete response

        Args:
            user_query: The user's question
            user_role: The user's role (for tool access control)

        Returns:
            AgentResponse with answer, plan, step results, and cost info
        """
        if not self._initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        logger.info(f"\n{'='*60}")
        logger.info(f"New query: {user_query}")
        logger.info(f"User role: {user_role.value}")
        logger.info(f"{'='*60}")

        # 1. Add to memory
        self.memory.add_user_message(user_query)

        # 2. Get available tools description (filtered by role)
        tools_desc = self.tool_registry.get_all_descriptions(user_role)

        # 3. Plan
        plan = self.planner.create_plan(
            query=user_query,
            tools_description=tools_desc,
            conversation_history=self.memory.get_history_string(),
        )
        logger.info(f"Plan: {len(plan.steps)} steps")
        for i, step in enumerate(plan.steps):
            logger.info(f"  Step {i+1}: {step.tool_name} â€” {step.reasoning}")

        # 4. Execute
        response = self.executor.execute_plan(plan, user_role)

        # 5. Update memory
        self.memory.add_assistant_message(response.answer)

        # 6. Log cost (simplified â€” in production you'd get actual token counts)
        self.cost_tracker.log_usage(
            model=settings.llm_model_name,
            input_tokens=response.total_tokens // 2 or 500,  # Estimate
            output_tokens=response.total_tokens // 2 or 500,
            query=user_query,
        )

        logger.info(f"Answer: {response.answer[:200]}...")
        return response

    def reset_conversation(self):
        """Clear conversation memory for a fresh start."""
        self.memory.clear()
        logger.info("Conversation memory cleared.")

