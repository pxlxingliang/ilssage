from abc import ABC, abstractmethod
from enum import Enum
from typing import AsyncIterator, Dict, List, Optional

from backend.core.events import AgentEvent
from backend.core.exceptions import AgentError
from backend.core.llm import LLMProvider
from backend.tools.registry import ToolRegistry


class AgentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class BaseAgent(ABC):
    def __init__(
        self,
        tools: Optional[ToolRegistry] = None,
        system_prompt: Optional[str] = None,
    ):
        self.tools = tools
        self.system_prompt = system_prompt or "You are a helpful assistant."
        self._state = AgentState.IDLE
        self._current_session_id: Optional[str] = None

    @property
    def state(self) -> AgentState:
        return self._state

    @abstractmethod
    async def run(
        self,
        messages: List[Dict],
        provider: LLMProvider,
        session_id: Optional[str] = None,
    ) -> str:
        ...

    @abstractmethod
    async def stream_run(
        self,
        messages: List[Dict],
        provider: LLMProvider,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[AgentEvent]:
        ...

    def cancel(self) -> None:
        self._state = AgentState.IDLE

    def pause(self) -> None:
        if self._state == AgentState.RUNNING:
            self._state = AgentState.PAUSED

    def resume(self) -> None:
        if self._state == AgentState.PAUSED:
            self._state = AgentState.RUNNING
