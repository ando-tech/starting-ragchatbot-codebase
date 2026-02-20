"""
Unit tests for RAGSystem.query() in rag_system.py.

VectorStore, AIGenerator, and DocumentProcessor are all patched at import
time so no real models, databases, or API calls are made.
"""
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Patch heavy dependencies before importing RAGSystem
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_heavy_imports():
    """
    Patch VectorStore and AIGenerator constructors so RAGSystem.__init__
    never instantiates real objects (which would load models, connect to DB, etc.).
    """
    with patch("rag_system.VectorStore") as mock_vs_cls, \
         patch("rag_system.AIGenerator") as mock_ai_cls, \
         patch("rag_system.DocumentProcessor") as mock_dp_cls:

        # Sensible defaults for the mocked instances
        mock_vs = MagicMock()
        mock_vs_cls.return_value = mock_vs

        mock_ai = MagicMock()
        mock_ai.generate_response.return_value = "Mocked AI answer"
        mock_ai_cls.return_value = mock_ai

        mock_dp = MagicMock()
        mock_dp_cls.return_value = mock_dp

        yield {
            "vector_store": mock_vs,
            "ai_generator": mock_ai,
            "document_processor": mock_dp,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config():
    """Minimal config-like object that satisfies RAGSystem.__init__."""
    cfg = MagicMock()
    cfg.CHUNK_SIZE = 800
    cfg.CHUNK_OVERLAP = 100
    cfg.MAX_RESULTS = 5
    cfg.MAX_HISTORY = 2
    cfg.CHROMA_PATH = "/tmp/test_chroma"
    cfg.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    cfg.ANTHROPIC_API_KEY = "sk-ant-test"
    cfg.ANTHROPIC_MODEL = "claude-test"
    return cfg


def _make_rag():
    from rag_system import RAGSystem
    return RAGSystem(_make_config())


# ---------------------------------------------------------------------------
# query() calls ai_generator correctly
# ---------------------------------------------------------------------------

class TestQueryCallsAIGenerator:
    def test_query_calls_ai_generator_with_tool_definitions(self, patch_heavy_imports):
        rag = _make_rag()
        mock_ai = patch_heavy_imports["ai_generator"]

        rag.query("What is RAG?")

        mock_ai.generate_response.assert_called_once()
        call_kwargs = mock_ai.generate_response.call_args[1]
        assert "tools" in call_kwargs
        assert "tool_manager" in call_kwargs


# ---------------------------------------------------------------------------
# query() return value
# ---------------------------------------------------------------------------

class TestQueryReturnValue:
    def test_query_returns_answer_and_sources_tuple(self, patch_heavy_imports):
        patch_heavy_imports["ai_generator"].generate_response.return_value = "Some answer"

        rag = _make_rag()
        # Inject known sources into the search tool
        rag.tool_manager.get_last_sources = MagicMock(return_value=[{"title": "Course A"}])

        result = rag.query("Explain vectors")

        assert isinstance(result, tuple)
        answer, sources = result
        assert isinstance(answer, str)
        assert isinstance(sources, list)

    def test_answer_matches_ai_generator_output(self, patch_heavy_imports):
        patch_heavy_imports["ai_generator"].generate_response.return_value = "Specific answer text"

        rag = _make_rag()
        answer, _ = rag.query("Any question")

        assert answer == "Specific answer text"


# ---------------------------------------------------------------------------
# Source management
# ---------------------------------------------------------------------------

class TestSourceManagement:
    def test_sources_retrieved_then_reset_per_query(self, patch_heavy_imports):
        rag = _make_rag()
        rag.tool_manager.get_last_sources = MagicMock(return_value=[])
        rag.tool_manager.reset_sources = MagicMock()

        rag.query("Any question")

        rag.tool_manager.get_last_sources.assert_called_once()
        rag.tool_manager.reset_sources.assert_called_once()

    def test_sources_returned_from_get_last_sources(self, patch_heavy_imports):
        expected_sources = [{"title": "RAG Course", "lesson_number": 2, "url": None}]

        rag = _make_rag()
        rag.tool_manager.get_last_sources = MagicMock(return_value=expected_sources)

        _, sources = rag.query("What does lesson 2 cover?")

        assert sources == expected_sources


# ---------------------------------------------------------------------------
# Session / conversation history handling
# ---------------------------------------------------------------------------

class TestSessionHandling:
    def test_session_history_passed_when_session_exists(self, patch_heavy_imports):
        mock_ai = patch_heavy_imports["ai_generator"]

        rag = _make_rag()
        rag.session_manager.get_conversation_history = MagicMock(return_value="User: Hi\nAssistant: Hello")

        rag.query("Follow up", session_id="session-abc")

        call_kwargs = mock_ai.generate_response.call_args[1]
        assert call_kwargs.get("conversation_history") == "User: Hi\nAssistant: Hello"

    def test_no_history_when_session_id_is_none(self, patch_heavy_imports):
        mock_ai = patch_heavy_imports["ai_generator"]

        rag = _make_rag()
        rag.query("First question", session_id=None)

        call_kwargs = mock_ai.generate_response.call_args[1]
        assert call_kwargs.get("conversation_history") is None

    def test_exchange_saved_to_session_after_query(self, patch_heavy_imports):
        patch_heavy_imports["ai_generator"].generate_response.return_value = "The answer"

        rag = _make_rag()
        rag.session_manager.add_exchange = MagicMock()

        rag.query("User question", session_id="session-xyz")

        rag.session_manager.add_exchange.assert_called_once_with(
            "session-xyz", "User question", "The answer"
        )

    def test_no_exchange_saved_when_no_session(self, patch_heavy_imports):
        rag = _make_rag()
        rag.session_manager.add_exchange = MagicMock()

        rag.query("Stateless question", session_id=None)

        rag.session_manager.add_exchange.assert_not_called()


# ---------------------------------------------------------------------------
# Error resilience
# ---------------------------------------------------------------------------

class TestErrorResilience:
    def test_search_error_does_not_raise_exception(self, patch_heavy_imports):
        """
        Even when the tool returns an error string (e.g. from MAX_RESULTS=0),
        RAGSystem.query() should complete without raising an exception.
        The AI generator still receives the error as a tool result and produces
        some response.
        """
        patch_heavy_imports["ai_generator"].generate_response.return_value = (
            "I was unable to find specific content."
        )

        rag = _make_rag()

        # Should not raise
        answer, sources = rag.query("Course question that triggers search error")

        assert isinstance(answer, str)
        assert isinstance(sources, list)
