"""
Integration tests for the FastAPI endpoints defined in app.py.

app.py is imported with all heavy dependencies mocked (see conftest.py):
  • RAGSystem components (VectorStore, AIGenerator, DocumentProcessor)
  • StaticFiles mount (../frontend does not exist in the test environment)

Tests use the `api_client` and `mock_rag_system` fixtures from conftest.py.
"""
import pytest


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    """Tests for POST /api/query."""

    def test_returns_200_with_valid_query(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("Some answer.", [])

        response = api_client.post("/api/query", json={"query": "What is RAG?"})

        assert response.status_code == 200

    def test_response_body_contains_answer(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("RAG stands for Retrieval-Augmented Generation.", [])

        response = api_client.post("/api/query", json={"query": "What is RAG?"})

        assert response.json()["answer"] == "RAG stands for Retrieval-Augmented Generation."

    def test_new_session_id_created_when_none_provided(self, api_client, mock_rag_system):
        mock_rag_system.session_manager.create_session.return_value = "new-session-abc"
        mock_rag_system.query.return_value = ("Answer", [])

        response = api_client.post("/api/query", json={"query": "Hello?"})

        assert response.json()["session_id"] == "new-session-abc"

    def test_existing_session_id_passed_through(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("Answer", [])

        response = api_client.post(
            "/api/query",
            json={"query": "Follow-up?", "session_id": "existing-session-xyz"},
        )

        assert response.json()["session_id"] == "existing-session-xyz"

    def test_create_session_not_called_when_session_id_provided(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("Answer", [])

        api_client.post(
            "/api/query",
            json={"query": "Follow-up?", "session_id": "existing-session-xyz"},
        )

        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_sources_returned_in_response(self, api_client, mock_rag_system):
        sources = [{"title": "RAG Course", "lesson_number": 1, "url": "https://example.com/lesson1"}]
        mock_rag_system.query.return_value = ("Answer with source.", sources)

        response = api_client.post("/api/query", json={"query": "Course question?"})
        data = response.json()

        assert len(data["sources"]) == 1
        assert data["sources"][0]["title"] == "RAG Course"
        assert data["sources"][0]["lesson_number"] == 1
        assert data["sources"][0]["url"] == "https://example.com/lesson1"

    def test_empty_sources_list_when_no_search_performed(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("General answer.", [])

        response = api_client.post("/api/query", json={"query": "What is 2 + 2?"})

        assert response.json()["sources"] == []

    def test_query_text_forwarded_to_rag_system(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("Answer", [])

        api_client.post("/api/query", json={"query": "How does vector search work?"})

        positional_args = mock_rag_system.query.call_args[0]
        assert "How does vector search work?" in positional_args[0]

    def test_session_id_forwarded_to_rag_system(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("Answer", [])

        api_client.post(
            "/api/query",
            json={"query": "Question?", "session_id": "my-session"},
        )

        _, forwarded_session = mock_rag_system.query.call_args[0]
        assert forwarded_session == "my-session"

    def test_returns_500_when_rag_system_raises(self, api_client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("DB connection failed")

        response = api_client.post("/api/query", json={"query": "Any question"})

        assert response.status_code == 500

    def test_500_response_includes_error_detail(self, api_client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("DB connection failed")

        response = api_client.post("/api/query", json={"query": "Any question"})

        assert "DB connection failed" in response.json()["detail"]

    def test_multiple_sources_all_present_in_response(self, api_client, mock_rag_system):
        sources = [
            {"title": "Course A", "lesson_number": 1, "url": None},
            {"title": "Course B", "lesson_number": 2, "url": "https://example.com"},
        ]
        mock_rag_system.query.return_value = ("Multi-source answer.", sources)

        response = api_client.post("/api/query", json={"query": "Cross-course question?"})
        data = response.json()

        assert len(data["sources"]) == 2
        assert data["sources"][0]["title"] == "Course A"
        assert data["sources"][1]["title"] == "Course B"


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:
    """Tests for GET /api/courses."""

    def test_returns_200(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 1,
            "course_titles": ["Intro to RAG"],
        }

        response = api_client.get("/api/courses")

        assert response.status_code == 200

    def test_total_courses_count_in_response(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["Course A", "Course B", "Course C"],
        }

        response = api_client.get("/api/courses")

        assert response.json()["total_courses"] == 3

    def test_course_titles_list_in_response(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Intro to RAG", "MCP Course"],
        }

        response = api_client.get("/api/courses")

        assert response.json()["course_titles"] == ["Intro to RAG", "MCP Course"]

    def test_empty_catalog_returns_zero_and_empty_list(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        response = api_client.get("/api/courses")
        data = response.json()

        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_returns_500_when_analytics_raises(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("ChromaDB unavailable")

        response = api_client.get("/api/courses")

        assert response.status_code == 500

    def test_500_response_includes_error_detail(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("ChromaDB unavailable")

        response = api_client.get("/api/courses")

        assert "ChromaDB unavailable" in response.json()["detail"]
