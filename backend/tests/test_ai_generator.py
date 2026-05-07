"""
Tests for AIGenerator in ai_generator.py.

Two tests here FAIL before the fix and PASS after:
  - test_handles_empty_content_gracefully_on_direct_path
  - test_handles_empty_final_content_after_tool_execution

Both fail because ai_generator.py:89 and :137 call `response.content[0].text`
without checking whether content is empty. When the Anthropic API returns
content=[], that raises IndexError, which propagates to app.py -> HTTP 500
-> frontend shows "Error: Query failed".
"""
import pytest
from unittest.mock import MagicMock
from conftest import make_text_message, make_tool_use_message, make_empty_content_message


class TestGenerateResponseDirectPath:
    """Tests for the non-tool path: stop_reason='end_turn'."""

    def test_returns_text_on_end_turn(self, ai_generator, mock_anthropic_client):
        mock_anthropic_client.messages.create.return_value = make_text_message("Hello!")
        result = ai_generator.generate_response(query="What is ML?")
        assert result == "Hello!"
        mock_anthropic_client.messages.create.assert_called_once()

    def test_handles_empty_content_gracefully_on_direct_path(
        self, ai_generator, mock_anthropic_client
    ):
        """
        FAILS before fix: ai_generator.py:89 raises IndexError when content=[].
        PASSES after adding:
            if not response.content:
                return "I was unable to generate a response. Please try again."
        """
        mock_anthropic_client.messages.create.return_value = make_empty_content_message()
        result = ai_generator.generate_response(query="What is ML?")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_tool_execution_when_stop_reason_is_end_turn(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Tool manager is not used when Claude returns end_turn (no tool use)."""
        mock_anthropic_client.messages.create.return_value = make_text_message("answer")
        result = ai_generator.generate_response(
            query="hello",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert mock_anthropic_client.messages.create.call_count == 1
        mock_tool_manager.execute_tool.assert_not_called()
        assert result == "answer"

    def test_conversation_history_appended_to_system_prompt(
        self, ai_generator, mock_anthropic_client
    ):
        mock_anthropic_client.messages.create.return_value = make_text_message("ok")
        ai_generator.generate_response(
            query="follow-up",
            conversation_history="User: What is ML?\nAssistant: ML is...",
        )
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert "User: What is ML?" in call_kwargs["system"]
        assert "Previous conversation:" in call_kwargs["system"]

    def test_no_history_in_system_prompt_when_none(self, ai_generator, mock_anthropic_client):
        mock_anthropic_client.messages.create.return_value = make_text_message("ok")
        ai_generator.generate_response(query="a question")
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert "Previous conversation:" not in call_kwargs["system"]


class TestToolCallLoop:
    """Tests for the agentic tool-call loop (up to MAX_TOOL_ROUNDS rounds)."""

    def test_tool_executed_and_result_fed_to_second_api_call(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        mock_anthropic_client.messages.create.side_effect = [
            make_tool_use_message("search_course_content", {"query": "backprop"}, "tu_1"),
            make_text_message("Backprop is an algorithm."),
        ]
        mock_tool_manager.execute_tool.return_value = "Backprop course content..."
        result = ai_generator.generate_response(
            query="What is backpropagation?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert mock_anthropic_client.messages.create.call_count == 2
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="backprop"
        )
        assert result == "Backprop is an algorithm."

    def test_handles_empty_final_content_after_tool_execution(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """
        FAILS before fix: ai_generator.py:137 raises IndexError when final content=[].
        PASSES after adding:
            if not final_response.content:
                return "I was unable to synthesize a response..."
        This is the primary cause of HTTP 500 -> "Error: Query failed" in the frontend.
        """
        mock_anthropic_client.messages.create.side_effect = [
            make_tool_use_message("search_course_content", {"query": "test"}, "tu_1"),
            make_empty_content_message(),
        ]
        mock_tool_manager.execute_tool.return_value = "some tool content"
        result = ai_generator.generate_response(
            query="test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tool_result_message_format_is_correct(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """The tool result passed to the second API call must follow Anthropic's format."""
        mock_anthropic_client.messages.create.side_effect = [
            make_tool_use_message("search_course_content", {"query": "test"}, "tu_abc"),
            make_text_message("Final answer"),
        ]
        mock_tool_manager.execute_tool.return_value = "tool content"
        ai_generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        second_call = mock_anthropic_client.messages.create.call_args_list[1][1]
        messages = second_call["messages"]
        tool_result_msg = messages[-1]
        assert tool_result_msg["role"] == "user"
        content = tool_result_msg["content"]
        assert len(content) == 1
        assert content[0]["type"] == "tool_result"
        assert content[0]["tool_use_id"] == "tu_abc"
        assert content[0]["content"] == "tool content"

    def test_round_calls_include_tools(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Each round call within MAX_TOOL_ROUNDS must include tool definitions so Claude
        can call another tool or answer directly."""
        mock_anthropic_client.messages.create.side_effect = [
            make_tool_use_message("search_course_content", {"query": "test"}, "tu_1"),
            make_text_message("Answer"),
        ]
        mock_tool_manager.execute_tool.return_value = "result"
        ai_generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        second_call = mock_anthropic_client.messages.create.call_args_list[1][1]
        assert "tools" in second_call
        assert "tool_choice" in second_call

    def test_assistant_tool_use_added_to_message_history(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """The assistant's tool_use block is included in the message history for the second call."""
        tool_msg = make_tool_use_message("search_course_content", {"query": "test"}, "tu_1")
        mock_anthropic_client.messages.create.side_effect = [
            tool_msg,
            make_text_message("Answer"),
        ]
        mock_tool_manager.execute_tool.return_value = "result"
        ai_generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        second_call = mock_anthropic_client.messages.create.call_args_list[1][1]
        messages = second_call["messages"]
        # messages: [user query, assistant tool_use, user tool_result]
        assert len(messages) == 3
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == tool_msg.content

    # --- Two-round (sequential) tests ---

    def test_two_round_tool_calls_makes_three_api_calls(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Two sequential tool calls require 3 API calls total: round 0, round 1, synthesis."""
        mock_anthropic_client.messages.create.side_effect = [
            make_tool_use_message("get_course_outline", {"course_name": "ML 101"}, "tu_1"),
            make_tool_use_message("search_course_content", {"query": "gradient descent"}, "tu_2"),
            make_text_message("Course X covers gradient descent in lesson 3."),
        ]
        mock_tool_manager.execute_tool.side_effect = [
            "Lesson 4: Gradient Descent",
            "Course X - Lesson 3 content...",
        ]
        result = ai_generator.generate_response(
            query="Find a course on the same topic as lesson 4 of ML 101",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert mock_anthropic_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2
        assert result == "Course X covers gradient descent in lesson 3."

    def test_second_round_api_call_includes_tools(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Round 1 call must still include tool definitions so Claude can call another tool."""
        mock_anthropic_client.messages.create.side_effect = [
            make_tool_use_message("get_course_outline", {"course_name": "ML 101"}, "tu_1"),
            make_tool_use_message("search_course_content", {"query": "topic"}, "tu_2"),
            make_text_message("Answer"),
        ]
        mock_tool_manager.execute_tool.return_value = "result"
        ai_generator.generate_response(
            query="test",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        second_call = mock_anthropic_client.messages.create.call_args_list[1][1]
        assert "tools" in second_call
        assert "tool_choice" in second_call

    def test_final_synthesis_call_has_no_tools_after_two_rounds(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """The synthesis call (third call when both rounds used tool_use) must not have tools."""
        mock_anthropic_client.messages.create.side_effect = [
            make_tool_use_message("get_course_outline", {"course_name": "ML 101"}, "tu_1"),
            make_tool_use_message("search_course_content", {"query": "topic"}, "tu_2"),
            make_text_message("Answer"),
        ]
        mock_tool_manager.execute_tool.return_value = "result"
        ai_generator.generate_response(
            query="test",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        synthesis_call = mock_anthropic_client.messages.create.call_args_list[2][1]
        assert "tools" not in synthesis_call
        assert "tool_choice" not in synthesis_call

    def test_full_message_history_sent_to_synthesis_call(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """After two tool rounds the synthesis call receives all 5 prior messages."""
        mock_anthropic_client.messages.create.side_effect = [
            make_tool_use_message("get_course_outline", {"course_name": "X"}, "tu_1"),
            make_tool_use_message("search_course_content", {"query": "topic"}, "tu_2"),
            make_text_message("Answer"),
        ]
        mock_tool_manager.execute_tool.side_effect = ["outline result", "search result"]
        ai_generator.generate_response(
            query="test",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        synthesis_call = mock_anthropic_client.messages.create.call_args_list[2][1]
        messages = synthesis_call["messages"]
        # [user_query, asst_R0, tool_result_R0, asst_R1, tool_result_R1]
        assert len(messages) == 5
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[3]["role"] == "assistant"
        assert messages[4]["role"] == "user"

    def test_early_exit_when_round1_returns_text_skips_synthesis(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """If Claude answers on round 1 (end_turn), no synthesis call is made."""
        mock_anthropic_client.messages.create.side_effect = [
            make_tool_use_message("search_course_content", {"query": "backprop"}, "tu_1"),
            make_text_message("Direct answer after seeing results."),
        ]
        mock_tool_manager.execute_tool.return_value = "search result"
        result = ai_generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert mock_anthropic_client.messages.create.call_count == 2
        assert result == "Direct answer after seeing results."

    def test_tool_execution_exception_terminates_loop_synthesis_still_runs(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """A tool that raises an exception stops further rounds; synthesis still runs."""
        mock_anthropic_client.messages.create.side_effect = [
            make_tool_use_message("search_course_content", {"query": "test"}, "tu_1"),
            make_text_message("Partial answer."),
        ]
        mock_tool_manager.execute_tool.side_effect = Exception("db error")
        result = ai_generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert mock_anthropic_client.messages.create.call_count == 2
        assert isinstance(result, str)
        assert len(result) > 0
        # Verify the error string was forwarded as tool result content
        second_call = mock_anthropic_client.messages.create.call_args_list[1][1]
        tool_result_content = second_call["messages"][-1]["content"][0]["content"]
        assert "Tool execution error:" in tool_result_content

    def test_cap_at_max_rounds(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Loop stops after MAX_TOOL_ROUNDS even if Claude keeps returning tool_use."""
        mock_anthropic_client.messages.create.side_effect = [
            make_tool_use_message("search_course_content", {"query": "q1"}, "tu_1"),
            make_tool_use_message("search_course_content", {"query": "q2"}, "tu_2"),
            make_text_message("Final synthesis."),
        ]
        mock_tool_manager.execute_tool.return_value = "result"
        result = ai_generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert mock_anthropic_client.messages.create.call_count == 3
        assert result == "Final synthesis."
