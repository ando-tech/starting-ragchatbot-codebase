"""
Shared fixtures and path setup for all backend tests.
"""
import sys
import os

# Add backend/ to sys.path so plain imports like `from vector_store import …` resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
