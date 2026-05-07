import anthropic
from typing import List, Optional, Tuple

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search & Outline Tool Usage:
- Use **search_course_content** only for questions about specific course topics or educational details
- Use **get_course_outline** for questions about course structure, lesson list, or course overview
- You may make up to 2 sequential tool calls when a query requires chained lookups
  (e.g. first retrieve a course outline to identify a lesson topic, then search for
  that topic in a second call)
- Only chain a second tool call when the first result is needed to form the second query
- For outline queries, present: course title, course link, and each lesson number with its title
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        messages = [{"role": "user", "content": query}]
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Agentic loop: up to MAX_TOOL_ROUNDS rounds with tools available
        for _round in range(self.MAX_TOOL_ROUNDS):
            response = self.client.messages.create(**api_params)

            # Condition B: direct answer or no tool manager to execute calls
            if response.stop_reason != "tool_use" or not tool_manager:
                break

            tool_results, had_failure = self._execute_tool_round(response, tool_manager)

            messages.append({"role": "assistant", "content": response.content})
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Condition C: tool execution failed — fall through to synthesis
            if had_failure:
                break
        # for-else (condition A): loop exhausted all rounds without a break;
        # response still has stop_reason="tool_use", so synthesis call follows below

        if response.stop_reason != "tool_use":
            if not response.content:
                return "I was unable to generate a response. Please try again."
            return response.content[0].text

        # Final synthesis call — no tools; Claude synthesizes from accumulated history
        final_params = {**self.base_params, "messages": messages, "system": system_content}
        final_response = self.client.messages.create(**final_params)
        if not final_response.content:
            return "I was unable to synthesize a response from the search results. Please try again."
        return final_response.content[0].text

    def _execute_tool_round(self, response, tool_manager) -> Tuple[list, bool]:
        """
        Execute all tool_use blocks in one Claude response.

        Returns:
            (tool_results, had_failure): list of Anthropic tool_result dicts and
            whether any tool raised an exception.
        """
        tool_results = []
        had_failure = False
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                result = tool_manager.execute_tool(block.name, **block.input)
            except Exception as e:
                result = f"Tool execution error: {e}"
                had_failure = True
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })
        return tool_results, had_failure
