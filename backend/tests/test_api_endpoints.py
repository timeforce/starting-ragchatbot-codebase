"""
Tests for FastAPI endpoints in app.py.

Uses `test_client` (TestClient wrapping the FastAPI app) and `mock_rag_system`
(a MagicMock replacing RAGSystem) — both provided by conftest.py.
No ChromaDB, Anthropic API, or filesystem access occurs.
"""
import pytest


class TestQueryEndpoint:
    """POST /api/query"""

    def test_returns_200_with_answer_sources_session(self, test_client):
        resp = test_client.post("/api/query", json={"query": "What is ML?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Test answer."
        assert isinstance(data["sources"], list)
        assert "session_id" in data

    def test_auto_creates_session_when_none_provided(self, test_client, mock_rag_system):
        resp = test_client.post("/api/query", json={"query": "Hello"})
        assert resp.status_code == 200
        mock_rag_system.session_manager.create_session.assert_called_once()
        assert resp.json()["session_id"] == "auto-session-001"

    def test_uses_provided_session_id(self, test_client, mock_rag_system):
        resp = test_client.post(
            "/api/query", json={"query": "Hello", "session_id": "my-session"}
        )
        assert resp.status_code == 200
        assert resp.json()["session_id"] == "my-session"
        # create_session must NOT be called when a session_id is already supplied
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_query_text_forwarded_to_rag_system(self, test_client, mock_rag_system):
        test_client.post("/api/query", json={"query": "Tell me about backprop"})
        first_positional_arg = mock_rag_system.query.call_args[0][0]
        assert "backprop" in first_positional_arg

    def test_returns_500_when_rag_raises(self, test_client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("db crashed")
        resp = test_client.post("/api/query", json={"query": "anything"})
        assert resp.status_code == 500

    def test_returns_422_when_query_field_missing(self, test_client):
        resp = test_client.post("/api/query", json={"session_id": "s1"})
        assert resp.status_code == 422


class TestCoursesEndpoint:
    """GET /api/courses"""

    def test_returns_200_with_course_stats(self, test_client):
        resp = test_client.get("/api/courses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_courses"] == 2
        assert data["course_titles"] == ["Course A", "Course B"]

    def test_calls_get_course_analytics(self, test_client, mock_rag_system):
        test_client.get("/api/courses")
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_returns_500_when_analytics_raises(self, test_client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("analytics error")
        resp = test_client.get("/api/courses")
        assert resp.status_code == 500


class TestClearSessionEndpoint:
    """POST /api/session/clear"""

    def test_returns_ok_on_success(self, test_client, mock_rag_system):
        resp = test_client.post(
            "/api/session/clear", json={"session_id": "sess-to-clear"}
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        mock_rag_system.session_manager.clear_session.assert_called_once_with(
            "sess-to-clear"
        )

    def test_returns_500_when_clear_raises(self, test_client, mock_rag_system):
        mock_rag_system.session_manager.clear_session.side_effect = RuntimeError("fail")
        resp = test_client.post(
            "/api/session/clear", json={"session_id": "bad-session"}
        )
        assert resp.status_code == 500

    def test_returns_422_when_session_id_missing(self, test_client):
        resp = test_client.post("/api/session/clear", json={})
        assert resp.status_code == 422
