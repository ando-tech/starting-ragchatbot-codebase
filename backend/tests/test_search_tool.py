"""
Unit tests for CourseSearchTool.execute() in search_tools.py.

VectorStore is mocked to keep these tests unit-level.
Two integration-style tests at the bottom probe the real config value
and actual ChromaDB behaviour with n_results=0.
"""
import pytest
from unittest.mock import MagicMock, patch

from search_tools import CourseSearchTool
from vector_store import SearchResults


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tool(store=None):
    """Return a CourseSearchTool with a mock (or provided) VectorStore."""
    if store is None:
        store = MagicMock()
    return CourseSearchTool(store)


# ---------------------------------------------------------------------------
# Happy-path formatting
# ---------------------------------------------------------------------------

class TestReturnsFormattedResultsOnValidQuery:
    def test_header_and_content_present(self, valid_search_results):
        store = MagicMock()
        store.search.return_value = valid_search_results
        store.get_lesson_link.return_value = "https://example.com/lesson1"

        tool = _make_tool(store)
        result = tool.execute(query="RAG basics")

        assert "[Intro to RAG - Lesson 1]" in result
        assert "Lesson content about RAG systems." in result

    def test_multiple_results_joined_by_double_newline(self, valid_search_results):
        store = MagicMock()
        store.search.return_value = valid_search_results
        store.get_lesson_link.return_value = None

        tool = _make_tool(store)
        result = tool.execute(query="embeddings")

        # Both chunks should appear, separated by blank line
        parts = result.split("\n\n")
        assert len(parts) == 2


# ---------------------------------------------------------------------------
# Empty and error results
# ---------------------------------------------------------------------------

class TestEmptyAndErrorResults:
    def test_returns_no_content_message_when_empty(self, empty_search_results):
        store = MagicMock()
        store.search.return_value = empty_search_results

        tool = _make_tool(store)
        result = tool.execute(query="something obscure")

        assert "No relevant content found" in result

    def test_no_content_message_includes_course_filter(self, empty_search_results):
        store = MagicMock()
        store.search.return_value = empty_search_results

        tool = _make_tool(store)
        result = tool.execute(query="topic", course_name="Intro to RAG")

        assert "Intro to RAG" in result

    def test_returns_error_string_when_search_fails(self, error_search_results):
        store = MagicMock()
        store.search.return_value = error_search_results

        tool = _make_tool(store)
        result = tool.execute(query="anything")

        assert "Search error" in result
        assert result == error_search_results.error


# ---------------------------------------------------------------------------
# Arguments forwarded to VectorStore
# ---------------------------------------------------------------------------

class TestArgumentForwarding:
    def test_passes_course_name_to_store(self, empty_search_results):
        store = MagicMock()
        store.search.return_value = empty_search_results

        tool = _make_tool(store)
        tool.execute(query="content", course_name="MCP Course")

        store.search.assert_called_once()
        _, kwargs = store.search.call_args
        assert kwargs.get("course_name") == "MCP Course"

    def test_passes_lesson_number_to_store(self, empty_search_results):
        store = MagicMock()
        store.search.return_value = empty_search_results

        tool = _make_tool(store)
        tool.execute(query="content", lesson_number=3)

        store.search.assert_called_once()
        _, kwargs = store.search.call_args
        assert kwargs.get("lesson_number") == 3


# ---------------------------------------------------------------------------
# Source tracking
# ---------------------------------------------------------------------------

class TestSourceTracking:
    def test_updates_last_sources_after_successful_search(self, valid_search_results):
        store = MagicMock()
        store.search.return_value = valid_search_results
        store.get_lesson_link.return_value = "https://example.com/lesson"

        tool = _make_tool(store)
        tool.execute(query="RAG")

        assert len(tool.last_sources) == 2
        assert tool.last_sources[0]["title"] == "Intro to RAG"
        assert tool.last_sources[0]["lesson_number"] == 1
        assert "url" in tool.last_sources[0]

    def test_last_sources_empty_before_any_call(self):
        tool = _make_tool()
        assert tool.last_sources == []

    def test_last_sources_empty_after_error_result(self, error_search_results):
        store = MagicMock()
        store.search.return_value = error_search_results

        tool = _make_tool(store)
        tool.execute(query="anything")

        # Error path returns early; last_sources should stay empty
        assert tool.last_sources == []


# ---------------------------------------------------------------------------
# Bug detector: real config MAX_RESULTS value
# ---------------------------------------------------------------------------

class TestRealConfigMaxResults:
    def test_real_config_max_results_is_positive(self):
        """
        Regression test for config.py bug: MAX_RESULTS was set to 0.
        ChromaDB raises ValueError when n_results=0.
        This test FAILS when the bug is present and PASSES after the fix.
        """
        import config
        assert config.config.MAX_RESULTS > 0, (
            f"MAX_RESULTS is {config.config.MAX_RESULTS}, must be > 0. "
            "ChromaDB requires n_results >= 1. "
            "Fix: change MAX_RESULTS: int = 0 → MAX_RESULTS: int = 5 in config.py"
        )


# ---------------------------------------------------------------------------
# Integration: ChromaDB rejects n_results=0
# ---------------------------------------------------------------------------

class TestVectorStoreSearchWithZeroNResults:
    def test_vector_store_search_with_zero_n_results_errors(self):
        """
        Confirms that passing n_results=0 to a ChromaDB collection raises an exception.
        This demonstrates the root cause of the 'Query failed' error seen in the UI.
        """
        import chromadb
        from chromadb.config import Settings

        # Use ephemeral in-memory client to avoid touching persistent DB
        client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
        collection = client.create_collection("test_zero_n_results")

        # Add a document so the collection is non-empty
        collection.add(documents=["test document"], ids=["doc1"])

        # n_results=0 must raise (ChromaDB enforces n_results >= 1)
        with pytest.raises(Exception):
            collection.query(query_texts=["test"], n_results=0)
