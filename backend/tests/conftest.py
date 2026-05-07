import sys
import pytest
from unittest.mock import MagicMock, patch


# --- Message builder helpers ---
# These build mock Anthropic API response objects with the right attribute structure.
# ai_generator.py accesses: .stop_reason, .content (list), block.type, block.text,
# block.id, block.name, block.input — all satisfied by MagicMock with explicit attrs.

def make_text_message(text: str):
    """Simulates a Claude response with stop_reason='end_turn' and a text block."""
    block = MagicMock()
    block.type = "text"
    block.text = text

    msg = MagicMock()
    msg.stop_reason = "end_turn"
    msg.content = [block]
    return msg


def make_tool_use_message(tool_name: str, tool_input: dict, tool_id: str = "tu_001"):
    """Simulates a Claude response with stop_reason='tool_use' and a tool_use block."""
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = tool_name
    block.input = tool_input

    msg = MagicMock()
    msg.stop_reason = "tool_use"
    msg.content = [block]
    return msg


def make_empty_content_message():
    """Simulates a Claude response with stop_reason='end_turn' but content=[] (the bug trigger)."""
    msg = MagicMock()
    msg.stop_reason = "end_turn"
    msg.content = []
    return msg


# --- Unit test fixtures ---

@pytest.fixture
def mock_anthropic_client():
    return MagicMock()


@pytest.fixture
def ai_generator(mock_anthropic_client):
    """Real AIGenerator instance with the Anthropic client replaced by a mock."""
    with patch("ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client):
        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="test-model")
    return gen


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.max_results = 5
    return store


@pytest.fixture
def mock_tool_manager():
    tm = MagicMock()
    tm.get_tool_definitions.return_value = [{"name": "search_course_content"}]
    tm.execute_tool.return_value = "Mocked tool result"
    tm.get_last_sources.return_value = []
    return tm


# --- API test fixtures ---

@pytest.fixture
def mock_rag_system():
    """Mocked RAGSystem for FastAPI endpoint tests."""
    mock = MagicMock()
    mock.query.return_value = (
        "Test answer.",
        [{"label": "Course A - Lesson 1", "url": "http://example.com/lesson1"}],
    )
    mock.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Course A", "Course B"],
    }
    mock.session_manager.create_session.return_value = "auto-session-001"
    return mock


@pytest.fixture
def test_client(mock_rag_system):
    """
    TestClient for the FastAPI app. RAGSystem is mocked (no ChromaDB / Anthropic
    calls) and StaticFiles is replaced with a stub so the missing ../frontend
    directory does not cause an ImportError.

    The app module is removed from sys.modules before import so each test gets
    a fresh app instance with the patches active.
    """
    from fastapi.testclient import TestClient

    sys.modules.pop("app", None)

    class _FakeStaticFiles:
        """Minimal ASGI stub — satisfies app.mount() without touching the filesystem."""
        def __init__(self, *args, **kwargs):
            pass

        async def __call__(self, scope, receive, send):
            from starlette.responses import Response
            await Response("", status_code=404)(scope, receive, send)

    with patch("rag_system.RAGSystem", return_value=mock_rag_system), \
         patch("fastapi.staticfiles.StaticFiles", _FakeStaticFiles):
        import app as _app
        with TestClient(_app.app) as client:
            yield client

    sys.modules.pop("app", None)
