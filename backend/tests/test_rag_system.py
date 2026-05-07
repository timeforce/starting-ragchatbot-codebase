"""
Integration-style tests for RAGSystem.query() in rag_system.py.

VectorStore, AIGenerator, SessionManager, and DocumentProcessor are all mocked,
so no ChromaDB or real API calls are made.

One test documents Bug 1 (MAX_RESULTS=0 passed to VectorStore) and will need
updating after the config fix. The tool_manager and CourseSearchTool instances
are real (they wrap the mocked VectorStore), so the orchestration is fully tested.
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def rag_config():
    cfg = MagicMock()
    cfg.ANTHROPIC_API_KEY = "test-key"
    cfg.ANTHROPIC_MODEL = "test-model"
    cfg.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    cfg.CHUNK_SIZE = 800
    cfg.CHUNK_OVERLAP = 100
    cfg.MAX_RESULTS = 5
    cfg.MAX_HISTORY = 2
    cfg.CHROMA_PATH = "/tmp/test_chroma"
    return cfg


@pytest.fixture
def buggy_rag_config():
    cfg = MagicMock()
    cfg.ANTHROPIC_API_KEY = "test-key"
    cfg.ANTHROPIC_MODEL = "test-model"
    cfg.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    cfg.CHUNK_SIZE = 800
    cfg.CHUNK_OVERLAP = 100
    cfg.MAX_RESULTS = 0   # Bug: causes n_results=0 in ChromaDB queries
    cfg.MAX_HISTORY = 2
    cfg.CHROMA_PATH = "/tmp/test_chroma"
    return cfg


@pytest.fixture
def rag_system(rag_config):
    with patch("rag_system.VectorStore") as MockVS, \
         patch("rag_system.AIGenerator") as MockAI, \
         patch("rag_system.SessionManager") as MockSM, \
         patch("rag_system.DocumentProcessor"):

        mock_vs = MagicMock()
        MockVS.return_value = mock_vs
        mock_ai = MagicMock()
        MockAI.return_value = mock_ai
        mock_sm = MagicMock()
        MockSM.return_value = mock_sm
        mock_sm.get_conversation_history.return_value = None

        from rag_system import RAGSystem
        system = RAGSystem(rag_config)
        system._mock_ai = mock_ai
        system._mock_sm = mock_sm
        system._mock_vs = mock_vs
        yield system


class TestRAGSystemQueryOrchestration:
    """Verifies RAGSystem.query() correctly coordinates all components."""

    def test_query_returns_response_and_sources_tuple(self, rag_system):
        rag_system._mock_ai.generate_response.return_value = "ML is a field of AI."
        response, sources = rag_system.query("What is ML?")
        assert response == "ML is a field of AI."
        assert isinstance(sources, list)

    def test_tools_and_tool_manager_passed_to_ai_generator(self, rag_system):
        """Without tools, Claude cannot search course content. This must always be wired up."""
        rag_system._mock_ai.generate_response.return_value = "answer"
        rag_system.query("What is machine learning?")
        call_kwargs = rag_system._mock_ai.generate_response.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] is not None and len(call_kwargs["tools"]) > 0
        assert "tool_manager" in call_kwargs
        assert call_kwargs["tool_manager"] is rag_system.tool_manager

    def test_session_history_fetched_and_forwarded_when_session_exists(self, rag_system):
        rag_system._mock_sm.get_conversation_history.return_value = (
            "User: prior question\nAssistant: prior answer"
        )
        rag_system._mock_ai.generate_response.return_value = "new answer"
        rag_system.query("follow up?", session_id="session_1")
        call_kwargs = rag_system._mock_ai.generate_response.call_args[1]
        assert "prior question" in call_kwargs.get("conversation_history", "")

    def test_no_history_forwarded_without_session_id(self, rag_system):
        rag_system._mock_ai.generate_response.return_value = "answer"
        rag_system.query("question with no session")
        call_kwargs = rag_system._mock_ai.generate_response.call_args[1]
        assert call_kwargs.get("conversation_history") is None

    def test_add_exchange_called_with_correct_args_on_success(self, rag_system):
        rag_system._mock_ai.generate_response.return_value = "Great answer."
        rag_system.query("a question", session_id="session_1")
        rag_system._mock_sm.add_exchange.assert_called_once_with(
            "session_1", "a question", "Great answer."
        )

    def test_sources_reset_after_retrieval(self, rag_system):
        """After query(), tool_manager sources must be cleared for the next query."""
        rag_system._mock_ai.generate_response.return_value = "answer"
        rag_system.query("test query")
        assert rag_system.tool_manager.get_last_sources() == []


class TestRAGSystemMaxResultsPassedToVectorStore:
    """
    Verifies that config.MAX_RESULTS is correctly passed through to VectorStore.
    Uses buggy_rag_config (MAX_RESULTS=0) and rag_config (MAX_RESULTS=5) to
    confirm the value flows from config into VectorStore.__init__().
    """

    def test_max_results_passed_to_vector_store_init(self, buggy_rag_config):
        """MAX_RESULTS=0 causes n_results=0 in ChromaDB queries (ChromaDB raises TypeError)."""
        with patch("rag_system.VectorStore") as MockVS, \
             patch("rag_system.AIGenerator"), \
             patch("rag_system.SessionManager"), \
             patch("rag_system.DocumentProcessor"):
            MockVS.return_value = MagicMock()
            from rag_system import RAGSystem
            RAGSystem(buggy_rag_config)
            init_args = MockVS.call_args[0]
            assert init_args[2] == buggy_rag_config.MAX_RESULTS

    def test_fixed_max_results_of_five_passed_to_vector_store(self, rag_config):
        """After fix: MAX_RESULTS=5 flows into VectorStore so searches return real content."""
        with patch("rag_system.VectorStore") as MockVS, \
             patch("rag_system.AIGenerator"), \
             patch("rag_system.SessionManager"), \
             patch("rag_system.DocumentProcessor"):
            MockVS.return_value = MagicMock()
            from rag_system import RAGSystem
            RAGSystem(rag_config)
            init_args = MockVS.call_args[0]
            assert init_args[2] == 5
