import inspect
import json
from typing import AsyncIterator, Dict, List, Optional

from backend.core.agent import BaseAgent, AgentState
from backend.core.events import AgentEvent, AgentEventType
from backend.core.token_counter import count_tokens


class ReActAgent(BaseAgent):

    def _make_tool_event(self, tool_name: str, result: str) -> AgentEvent:
        display = result[:500] if result else "Tool returned empty result"
        return AgentEvent(
            type=AgentEventType.TOOL_CALL_END,
            data={
                "tool_name": tool_name,
                "result": display,
            },
        )

    async def _execute_tool(
        self, tool_name: str, arguments: str
    ) -> str:
        if not self.tools:
            return "No tools configured"
        tool_info = self.tools.get(tool_name)
        if not tool_info:
            return f"Tool '{tool_name}' not found"
        try:
            args = json.loads(arguments) if arguments else {}
            result = tool_info.execute(**args)
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, (dict, list)):
                return json.dumps(result, ensure_ascii=False, default=str)
            return str(result)
        except Exception as e:
            return f"Error calling tool '{tool_name}': {e}"

    async def run(
        self,
        messages: List[Dict],
        provider,
        session_id: Optional[str] = None,
    ) -> str:
        self._current_session_id = session_id
        self._state = AgentState.RUNNING
        tools = self.tools.to_openai_tools() if self.tools else None
        full_messages = [{"role": "system", "content": self.system_prompt}]
        full_messages += messages
        loop_messages = list(full_messages)

        try:
            while self._state == AgentState.RUNNING:
                response = await provider.async_client.chat.completions.create(
                    model=provider.model_name,
                    messages=loop_messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                )
                choice = response.choices[0]
                msg = choice.message

                if msg.tool_calls:
                    tool_calls_list = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                    loop_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls_list,
                    })

                    for tc in msg.tool_calls:
                        tool_name = tc.function.name
                        result = await self._execute_tool(
                            tool_name, tc.function.arguments
                        )
                        loop_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        })
                    continue
                else:
                    content = msg.content or ""
                    return content
        finally:
            self._state = AgentState.IDLE

    async def stream_run(
        self,
        messages: List[Dict],
        provider,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[AgentEvent]:
        self._current_session_id = session_id
        self._state = AgentState.RUNNING
        tools = self.tools.to_openai_tools() if self.tools else None
        full_messages = [{"role": "system", "content": self.system_prompt}]
        full_messages += messages
        loop_messages = list(full_messages)

        model_name = provider.model_name
        prompt_tokens = count_tokens(full_messages, model_name)

        try:
            while self._state == AgentState.RUNNING:
                if self._state == AgentState.PAUSED:
                    break

                stream = await provider.async_client.chat.completions.create(
                    model=model_name,
                    messages=loop_messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    stream=True,
                    stream_options={"include_usage": True},
                )

                tool_calls_acc: dict = {}
                text_content = ""
                reasoning_content = ""
                current_tool_id = None

                async for chunk in stream:
                    if self._state != AgentState.RUNNING:
                        break

                    if chunk.usage:
                        from backend.core.llm import ProviderUsage

                        provider._last_usage = ProviderUsage(
                            prompt_tokens=chunk.usage.prompt_tokens or 0,
                            completion_tokens=chunk.usage.completion_tokens or 0,
                            total_tokens=chunk.usage.total_tokens or 0,
                        )

                    if not chunk.choices:
                        continue

                    delta = chunk.choices[0].delta

                    if delta.content:
                        text_content += delta.content
                        yield AgentEvent(
                            type=AgentEventType.CONTENT_CHUNK,
                            data={"text": delta.content},
                        )

                    if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                        reasoning_content += delta.reasoning_content
                        yield AgentEvent(
                            type=AgentEventType.REASONING_CHUNK,
                            data={"text": delta.reasoning_content},
                        )

                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            tc_id = tc.id or current_tool_id
                            if tc_id and tc_id not in tool_calls_acc:
                                tool_calls_acc[tc_id] = {
                                    "id": tc_id,
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                                current_tool_id = tc_id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls_acc[
                                        tc_id or current_tool_id
                                    ]["function"]["name"] += tc.function.name
                                if tc.function.arguments:
                                    tool_calls_acc[
                                        tc_id or current_tool_id
                                    ]["function"]["arguments"] += tc.function.arguments

                if self._state != AgentState.RUNNING:
                    break

                if tool_calls_acc:
                    tool_call_list = list(tool_calls_acc.values())
                    loop_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_call_list,
                    })

                    for tc in tool_call_list:
                        func_info = tc["function"]
                        tool_name = func_info["name"]

                        yield AgentEvent(
                            type=AgentEventType.TOOL_CALL_START,
                            data={
                                "tool_call_id": tc["id"],
                                "tool_name": tool_name,
                                "args": func_info["arguments"],
                            },
                        )

                        result = await self._execute_tool(
                            tool_name, func_info["arguments"]
                        )
                        yield self._make_tool_event(tool_name, result)

                        loop_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                        })

                    continue
                else:
                    if text_content:
                        usage = provider.last_usage
                        done_data: dict = {
                            "full_text": text_content,
                            "prompt_tokens": prompt_tokens,
                        }
                        if usage:
                            done_data["usage"] = usage.to_dict()
                        yield AgentEvent(
                            type=AgentEventType.DONE,
                            data=done_data,
                        )
                    break

        except Exception as e:
            self._state = AgentState.ERROR
            yield AgentEvent(
                type=AgentEventType.ERROR,
                data={"message": str(e)},
            )
        finally:
            if self._state != AgentState.ERROR:
                self._state = AgentState.IDLE
