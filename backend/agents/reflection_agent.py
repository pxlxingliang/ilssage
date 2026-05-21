from typing import AsyncIterator, Dict, List, Optional

from backend.core.agent import BaseAgent
from backend.core.events import AgentEvent


class ReflectionAgent(BaseAgent):
    async def run(
        self, messages: List[Dict], session_id: Optional[str] = None
    ) -> str:
        raise NotImplementedError("ReflectionAgent is not yet implemented")

    async def stream_run(
        self, messages: List[Dict], session_id: Optional[str] = None
    ) -> AsyncIterator[AgentEvent]:
        raise NotImplementedError("ReflectionAgent is not yet implemented")
