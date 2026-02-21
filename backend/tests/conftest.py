"""
Shared fixtures and path setup for all backend tests.
"""
import sys
import os

# Add backend/ to sys.path so plain imports like `from vector_store import …` resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Imports needed for API fixtures (must come before `import app`)
# ---------------------------------------------------------------------------
from unittest.mock import MagicMock, patch as _patch

import pytest
from vector_store import SearchResults
from models import Course, Lesson, CourseChunk


# ---------------------------------------------------------------------------
# SearchResults fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_search_results():
    """A SearchResults with two documents and matching metadata."""
    return SearchResults(
        documents=["Lesson content about RAG systems.", "More content about embeddings."],
        metadata=[
            {"course_title": "Intro to RAG", "lesson_number": 1},
            {"course_title": "Intro to RAG", "lesson_number": 2},
        ],
        distances=[0.1, 0.3],
    )


@pytest.fixture
def empty_search_results():
    """A SearchResults with no documents."""
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def error_search_results():
    """A SearchResults carrying an error message."""
    return SearchResults.empty("Search error: n_results must be a positive integer")


# ---------------------------------------------------------------------------
# Course / Lesson / CourseChunk fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_lesson():
    return Lesson(
        lesson_number=1,
        title="Introduction to Vectors",
        content="Vectors are mathematical objects used in ML.",
        lesson_link="https://example.com/lesson1",
    )


@pytest.fixture
def sample_course(sample_lesson):
    return Course(
        title="Intro to RAG",
        instructor="Jane Doe",
        course_link="https://example.com/course",
        lessons=[sample_lesson],
    )


@pytest.fixture
def sample_chunk():
    return CourseChunk(
        course_title="Intro to RAG",
        lesson_number=1,
        content="Vectors are mathematical objects used in ML.",
        chunk_index=0,
    )


# ---------------------------------------------------------------------------
# API test fixtures
#
# app.py executes module-level code on first import:
#   • rag_system = RAGSystem(config)  → loads VectorStore (ChromaDB + embeddings)
#                                        and AIGenerator (Anthropic client)
#   • app.mount("/", StaticFiles(…))  → checks that ../frontend/ exists
#
# Patching the four targets below before importing `app` prevents all of that
# without changing behaviour for the other unit-test modules.
# ---------------------------------------------------------------------------

_vs_patcher     = _patch("rag_system.VectorStore")
_ai_patcher     = _patch("rag_system.AIGenerator")
_dp_patcher     = _patch("rag_system.DocumentProcessor")
_static_patcher = _patch("fastapi.staticfiles.StaticFiles")

_vs_patcher.start()
_ai_patcher.start()
_dp_patcher.start()
_static_patcher.start()

import app as _app_module  # safe to import now that heavy deps are mocked

_vs_patcher.stop()
_ai_patcher.stop()
_dp_patcher.stop()
_static_patcher.stop()

# Replace the module-level RAGSystem instance with a single shared MagicMock.
# Every API fixture test resets this mock before use (see mock_rag_system below).
_shared_mock_rag = MagicMock()
_app_module.rag_system = _shared_mock_rag


@pytest.fixture
def mock_rag_system():
    """
    The MagicMock that stands in for app.rag_system.
    Reset to a clean state with sensible defaults before every test.
    """
    _shared_mock_rag.reset_mock()
    # reset_mock() does not clear side_effect; do it explicitly so a test that
    # sets side_effect cannot bleed into the next test.
    _shared_mock_rag.query.side_effect = None
    _shared_mock_rag.get_course_analytics.side_effect = None
    _shared_mock_rag.session_manager.create_session.side_effect = None
    _shared_mock_rag.session_manager.create_session.return_value = "test-session-id"
    _shared_mock_rag.query.return_value = ("Default answer", [])
    _shared_mock_rag.get_course_analytics.return_value = {
        "total_courses": 0,
        "course_titles": [],
    }
    return _shared_mock_rag


@pytest.fixture
def api_client(mock_rag_system):
    """Starlette TestClient for the FastAPI app with all heavy deps mocked."""
    from starlette.testclient import TestClient
    return TestClient(_app_module.app)
