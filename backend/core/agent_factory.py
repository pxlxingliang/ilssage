from typing import Optional

from backend.core.agent import BaseAgent


class AgentFactory:
    """Encapsulates agent creation config. Each create() call returns a fresh agent."""

    def __init__(self, behavior: str, llm_service, session_service):
        self._behavior = behavior
        self._llm = llm_service
        self._session = session_service

    def create(
        self,
        system_prompt: Optional[str] = None,
        model_id: str = "",
    ) -> BaseAgent:
        from backend.agents import create_agent

        provider = self._llm.get_provider(model_id or None)

        return create_agent(
            self._behavior,
            provider,
            session_service=self._session,
            system_prompt=system_prompt,
        )
