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


# --- Fixtures ---

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
