"""
Unit tests for AIGenerator.generate_response() in ai_generator.py.

All Anthropic API calls are mocked via unittest.mock.patch so no real
network requests are made and no API key is needed.
"""
import pytest
from unittest.mock import MagicMock, patch, call

from ai_generator import AIGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_API_KEY = "sk-ant-test-key"
FAKE_MODEL = "claude-test-model"


def _make_generator():
    return AIGenerator(api_key=FAKE_API_KEY, model=FAKE_MODEL)


def _mock_end_turn_response(text="Direct answer."):
    """Build a mock Anthropic response that signals end_turn (no tool use)."""
    content_block = MagicMock()
    content_block.type = "text"
    content_block.text = text

    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [content_block]
    return response


def _mock_tool_use_response(tool_name="search_course_content", tool_input=None, tool_id="toolu_001"):
    """Build a mock Anthropic response that signals tool_use."""
    if tool_input is None:
        tool_input = {"query": "RAG basics"}

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.input = tool_input
    tool_block.id = tool_id

    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [tool_block]
    return response


# ---------------------------------------------------------------------------
# First API call structure
# ---------------------------------------------------------------------------

class TestFirstApiCallStructure:
    def test_first_api_call_includes_tools_and_auto_choice(self):
        gen = _make_generator()
        tools = [{"name": "search_course_content", "description": "...", "input_schema": {}}]
        tool_manager = MagicMock()
        end_turn = _mock_end_turn_response()

        with patch.object(gen.client.messages, "create", return_value=end_turn) as mock_create:
            gen.generate_response(query="What is RAG?", tools=tools, tool_manager=tool_manager)

        first_call_kwargs = mock_create.call_args_list[0][1]
        assert first_call_kwargs["tools"] == tools
        assert first_call_kwargs["tool_choice"] == {"type": "auto"}

    def test_no_tools_param_when_tools_not_provided(self):
        gen = _make_generator()
        end_turn = _mock_end_turn_response()

        with patch.object(gen.client.messages, "create", return_value=end_turn) as mock_create:
            gen.generate_response(query="Hello, how are you?")

        first_call_kwargs = mock_create.call_args_list[0][1]
        assert "tools" not in first_call_kwargs
        assert "tool_choice" not in first_call_kwargs


# ---------------------------------------------------------------------------
# Two-call path (tool_use → follow-up)
# ---------------------------------------------------------------------------

class TestTwoCallPath:
    def test_content_question_triggers_two_api_calls(self):
        gen = _make_generator()
        tools = [{"name": "search_course_content"}]
        tool_use_resp = _mock_tool_use_response()
        final_resp = _mock_end_turn_response("Here is the answer about RAG.")

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Some search results"

        with patch.object(gen.client.messages, "create", side_effect=[tool_use_resp, final_resp]) as mock_create:
            gen.generate_response(query="What does lesson 1 cover?", tools=tools, tool_manager=tool_manager)

        assert mock_create.call_count == 2

    def test_tool_manager_called_with_correct_tool_name_and_args(self):
        gen = _make_generator()
        tools = [{"name": "search_course_content"}]
        tool_input = {"query": "embeddings", "course_name": "Intro to RAG"}
        tool_use_resp = _mock_tool_use_response(tool_input=tool_input)
        final_resp = _mock_end_turn_response()

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Results"

        with patch.object(gen.client.messages, "create", side_effect=[tool_use_resp, final_resp]):
            gen.generate_response(query="Explain embeddings", tools=tools, tool_manager=tool_manager)

        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", **tool_input
        )

    def test_tool_result_sent_in_second_api_call_messages(self):
        gen = _make_generator()
        tools = [{"name": "search_course_content"}]
        tool_use_resp = _mock_tool_use_response(tool_id="toolu_XYZ")
        final_resp = _mock_end_turn_response()

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Relevant search content"

        with patch.object(gen.client.messages, "create", side_effect=[tool_use_resp, final_resp]) as mock_create:
            gen.generate_response(query="course content question", tools=tools, tool_manager=tool_manager)

        second_call_messages = mock_create.call_args_list[1][1]["messages"]

        # Find the tool_result message (sent as user role)
        tool_result_msg = None
        for msg in second_call_messages:
            if msg["role"] == "user" and isinstance(msg["content"], list):
                for block in msg["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tool_result_msg = block
                        break

        assert tool_result_msg is not None
        assert tool_result_msg["tool_use_id"] == "toolu_XYZ"
        assert tool_result_msg["content"] == "Relevant search content"



# ---------------------------------------------------------------------------
# Single-call path (end_turn, no tool use)
# ---------------------------------------------------------------------------

class TestSingleCallPath:
    def test_general_question_answered_in_single_call(self):
        gen = _make_generator()
        tools = [{"name": "search_course_content"}]
        end_turn = _mock_end_turn_response("The capital of France is Paris.")

        tool_manager = MagicMock()

        with patch.object(gen.client.messages, "create", return_value=end_turn) as mock_create:
            gen.generate_response(query="What is the capital of France?", tools=tools, tool_manager=tool_manager)

        assert mock_create.call_count == 1
        tool_manager.execute_tool.assert_not_called()

    def test_response_text_extracted_from_content_block_single_call(self):
        gen = _make_generator()
        end_turn = _mock_end_turn_response("Direct answer text.")

        with patch.object(gen.client.messages, "create", return_value=end_turn):
            result = gen.generate_response(query="Simple question?")

        assert result == "Direct answer text."

    def test_response_text_extracted_from_content_block_two_call(self):
        gen = _make_generator()
        tools = [{"name": "search_course_content"}]
        tool_use_resp = _mock_tool_use_response()
        final_resp = _mock_end_turn_response("Final synthesized answer.")

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "search data"

        with patch.object(gen.client.messages, "create", side_effect=[tool_use_resp, final_resp]):
            result = gen.generate_response(query="course question", tools=tools, tool_manager=tool_manager)

        assert result == "Final synthesized answer."


# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------

class TestConversationHistory:
    def test_conversation_history_appended_to_system_prompt(self):
        gen = _make_generator()
        end_turn = _mock_end_turn_response()
        history = "User: Hi\nAssistant: Hello!"

        with patch.object(gen.client.messages, "create", return_value=end_turn) as mock_create:
            gen.generate_response(query="Follow-up question", conversation_history=history)

        system_content = mock_create.call_args_list[0][1]["system"]
        assert history in system_content

    def test_no_history_means_plain_system_prompt(self):
        gen = _make_generator()
        end_turn = _mock_end_turn_response()

        with patch.object(gen.client.messages, "create", return_value=end_turn) as mock_create:
            gen.generate_response(query="A question")

        system_content = mock_create.call_args_list[0][1]["system"]
        # Should be exactly the static SYSTEM_PROMPT with no history appended
        assert system_content == AIGenerator.SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Round 1 keeps tools in the second API call
# ---------------------------------------------------------------------------

class TestOneRoundToolCallKeepsTools:
    """When round 0 returns tool_use and round 1 returns end_turn, the round-1
    call must still carry tools and tool_choice."""

    def test_round_1_call_has_tools(self):
        gen = _make_generator()
        tools = [{"name": "search_course_content"}]
        tool_use_resp = _mock_tool_use_response()
        end_turn_resp = _mock_end_turn_response("Answer after one tool.")

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "search results"

        with patch.object(gen.client.messages, "create",
                          side_effect=[tool_use_resp, end_turn_resp]) as mock_create:
            gen.generate_response(query="course question", tools=tools, tool_manager=tool_manager)

        assert mock_create.call_count == 2
        round_1_kwargs = mock_create.call_args_list[1][1]
        assert "tools" in round_1_kwargs
        assert "tool_choice" in round_1_kwargs

    def test_round_1_returns_end_turn_text(self):
        gen = _make_generator()
        tools = [{"name": "search_course_content"}]
        tool_use_resp = _mock_tool_use_response()
        end_turn_resp = _mock_end_turn_response("Final answer here.")

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "results"

        with patch.object(gen.client.messages, "create",
                          side_effect=[tool_use_resp, end_turn_resp]):
            result = gen.generate_response(query="course question", tools=tools, tool_manager=tool_manager)

        assert result == "Final answer here."


# ---------------------------------------------------------------------------
# Two-round tool path (MAX_ROUNDS exhausted → force-answer call)
# ---------------------------------------------------------------------------

class TestTwoRoundToolPath:
    """When both rounds return tool_use, MAX_ROUNDS is exhausted and a third
    force-answer call (without tools) is made."""

    def _setup(self):
        gen = _make_generator()
        tools = [{"name": "search_course_content"}]
        tool_use_1 = _mock_tool_use_response(tool_name="get_course_outline",
                                              tool_input={"course_name": "Intro to RAG"},
                                              tool_id="toolu_001")
        tool_use_2 = _mock_tool_use_response(tool_name="search_course_content",
                                              tool_input={"query": "lesson 1"},
                                              tool_id="toolu_002")
        end_turn = _mock_end_turn_response("Synthesized final answer.")
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "tool output"
        return gen, tools, [tool_use_1, tool_use_2, end_turn], tool_manager

    def test_two_tool_rounds_three_api_calls(self):
        gen, tools, side_effects, tool_manager = self._setup()

        with patch.object(gen.client.messages, "create",
                          side_effect=side_effects) as mock_create:
            gen.generate_response(query="cross-course query", tools=tools, tool_manager=tool_manager)

        assert mock_create.call_count == 3
        assert tool_manager.execute_tool.call_count == 2

    def test_round_2_call_includes_tools(self):
        gen, tools, side_effects, tool_manager = self._setup()

        with patch.object(gen.client.messages, "create",
                          side_effect=side_effects) as mock_create:
            gen.generate_response(query="cross-course query", tools=tools, tool_manager=tool_manager)

        round_2_kwargs = mock_create.call_args_list[1][1]
        assert "tools" in round_2_kwargs
        assert "tool_choice" in round_2_kwargs

    def test_force_answer_call_has_no_tools(self):
        gen, tools, side_effects, tool_manager = self._setup()

        with patch.object(gen.client.messages, "create",
                          side_effect=side_effects) as mock_create:
            gen.generate_response(query="cross-course query", tools=tools, tool_manager=tool_manager)

        force_answer_kwargs = mock_create.call_args_list[2][1]
        assert "tools" not in force_answer_kwargs
        assert "tool_choice" not in force_answer_kwargs

    def test_messages_accumulate_across_rounds(self):
        gen, tools, side_effects, tool_manager = self._setup()

        with patch.object(gen.client.messages, "create",
                          side_effect=side_effects) as mock_create:
            gen.generate_response(query="cross-course query", tools=tools, tool_manager=tool_manager)

        # Force-answer call (index 2) must have 5 messages:
        # user, assistant-1, user-results-1, assistant-2, user-results-2
        force_answer_messages = mock_create.call_args_list[2][1]["messages"]
        assert len(force_answer_messages) == 5

    def test_two_round_returns_final_text(self):
        gen, tools, side_effects, tool_manager = self._setup()

        with patch.object(gen.client.messages, "create",
                          side_effect=side_effects):
            result = gen.generate_response(query="cross-course query", tools=tools, tool_manager=tool_manager)

        assert result == "Synthesized final answer."


# ---------------------------------------------------------------------------
# Tool error handling
# ---------------------------------------------------------------------------

class TestToolErrorHandling:
    """Tool execution errors are caught and fed back as strings; they must
    never propagate to the caller."""

    def test_tool_error_does_not_raise(self):
        gen = _make_generator()
        tools = [{"name": "search_course_content"}]
        tool_use_resp = _mock_tool_use_response()
        end_turn_resp = _mock_end_turn_response("Answer despite error.")

        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ValueError("db down")

        with patch.object(gen.client.messages, "create",
                          side_effect=[tool_use_resp, end_turn_resp]):
            # Must not raise
            result = gen.generate_response(query="question", tools=tools, tool_manager=tool_manager)

        assert isinstance(result, str)

    def test_tool_error_string_in_messages(self):
        gen = _make_generator()
        tools = [{"name": "search_course_content"}]
        tool_use_resp = _mock_tool_use_response(tool_id="toolu_err")
        end_turn_resp = _mock_end_turn_response()

        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ValueError("db down")

        with patch.object(gen.client.messages, "create",
                          side_effect=[tool_use_resp, end_turn_resp]) as mock_create:
            gen.generate_response(query="question", tools=tools, tool_manager=tool_manager)

        second_call_messages = mock_create.call_args_list[1][1]["messages"]
        tool_result_content = None
        for msg in second_call_messages:
            if msg["role"] == "user" and isinstance(msg["content"], list):
                for block in msg["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tool_result_content = block["content"]
                        break

        assert tool_result_content is not None
        assert "Tool execution error" in tool_result_content

    def test_tool_error_round_1_still_two_calls(self):
        gen = _make_generator()
        tools = [{"name": "search_course_content"}]
        tool_use_resp = _mock_tool_use_response()
        end_turn_resp = _mock_end_turn_response()

        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ValueError("db down")

        with patch.object(gen.client.messages, "create",
                          side_effect=[tool_use_resp, end_turn_resp]) as mock_create:
            gen.generate_response(query="question", tools=tools, tool_manager=tool_manager)

        assert mock_create.call_count == 2

    def test_tool_error_round_2(self):
        gen = _make_generator()
        tools = [{"name": "search_course_content"}]
        tool_use_1 = _mock_tool_use_response(tool_name="get_course_outline",
                                              tool_input={"course_name": "Intro"},
                                              tool_id="toolu_001")
        tool_use_2 = _mock_tool_use_response(tool_id="toolu_002")
        end_turn = _mock_end_turn_response("Final answer.")

        tool_manager = MagicMock()
        # First call succeeds, second raises
        tool_manager.execute_tool.side_effect = ["outline results", ValueError("index error")]

        with patch.object(gen.client.messages, "create",
                          side_effect=[tool_use_1, tool_use_2, end_turn]) as mock_create:
            result = gen.generate_response(query="cross query", tools=tools, tool_manager=tool_manager)

        assert mock_create.call_count == 3
        assert isinstance(result, str)
