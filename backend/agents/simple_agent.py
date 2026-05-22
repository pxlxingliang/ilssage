from typing import AsyncIterator, Dict, List, Optional

from backend.core.agent import BaseAgent, AgentState
from backend.core.events import AgentEvent, AgentEventType
from backend.core.token_counter import count_tokens


class SimpleAgent(BaseAgent):
    async def run(
        self,
        messages: List[Dict],
        provider,
        session_id: Optional[str] = None,
    ) -> str:
        self._current_session_id = session_id
        self._state = AgentState.RUNNING
        try:
            result = await provider.ainvoke(messages)
            return result
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

        system_messages = [{"role": "system", "content": self.system_prompt}]
        full_messages = system_messages + messages
        prompt_tokens = count_tokens(full_messages, provider.model_name)

        try:
            accumulated = ""
            async for chunk in provider.astream_invoke(messages):
                if self._state == AgentState.PAUSED:
                    break
                accumulated += chunk
                yield AgentEvent(
                    type=AgentEventType.CONTENT_CHUNK,
                    data={"text": chunk},
                )
            done_data: dict = {
                "full_text": accumulated,
                "prompt_tokens": prompt_tokens,
            }
            usage = provider.last_usage
            if usage:
                done_data["usage"] = usage.to_dict()
            yield AgentEvent(
                type=AgentEventType.DONE,
                data=done_data,
            )
        except Exception as e:
            self._state = AgentState.ERROR
            yield AgentEvent(
                type=AgentEventType.ERROR,
                data={"message": str(e)},
            )
        finally:
            if self._state != AgentState.ERROR:
                self._state = AgentState.IDLE
