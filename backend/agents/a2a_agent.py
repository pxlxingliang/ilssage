from typing import Dict, List, Optional

from loguru import logger

from backend.roles import AgentCapability
from backend.tools.registry import ToolInfo, ToolRegistry


class SubAgentManager:

    def __init__(self, session_service):
        self._session_service = session_service
        self._tools: Dict[str, ToolRegistry] = {}
        self._capabilities: Dict[str, AgentCapability] = {}

    def register(
        self, capability: AgentCapability, tools: ToolRegistry
    ) -> None:
        self._capabilities[capability.name] = capability
        self._tools[capability.name] = tools
        logger.info(f"Registered sub-agent: {capability.name}")

    def get_capability(self, name: str) -> Optional[AgentCapability]:
        return self._capabilities.get(name)

    def list_capabilities(self) -> List[AgentCapability]:
        return list(self._capabilities.values())

    async def delegate(
        self, session_id: str, agent_name: str, task: str
    ) -> str:
        capability = self._capabilities.get(agent_name)
        tools = self._tools.get(agent_name)
        if capability is None or tools is None:
            return (
                f"Unknown sub-agent '{agent_name}'. "
                f"Available: {', '.join(self._capabilities.keys())}"
            )

        messages = self._session_service.get_messages(
            session_id, agent_name=agent_name
        )
        if not messages:
            messages = [
                {"role": "system", "content": capability.system_prompt}
            ]

        self._session_service.add_message(
            session_id, "user", task, agent_name=agent_name
        )

        from backend.deps import get_llm_service
        from backend.agents.react_agent import ReActAgent

        llm = get_llm_service()
        if capability.model_override:
            provider = llm.get_provider(capability.model_override)
        else:
            provider = llm.get_provider()

        sub_agent = ReActAgent(provider, tools, capability.system_prompt)

        try:
            result = await sub_agent.run(messages, session_id=session_id)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            result = f"Sub-agent '{agent_name}' failed: {error_msg}"
            logger.warning(f"Sub-agent '{agent_name}' failed: {e}")

        self._session_service.add_message(
            session_id, "assistant", result, agent_name=agent_name
        )

        return result


def add_agent_delegate_tool(agent, sub_agent_manager: SubAgentManager) -> None:
    caps = sub_agent_manager.list_capabilities()
    if not caps:
        return

    names = [c.name for c in caps]
    lines = [f"  - {c.name}: {c.description}" for c in caps]

    async def _agent_delegate_fn(agent_name: str, task: str) -> str:
        return await sub_agent_manager.delegate(
            agent._current_session_id, agent_name, task
        )

    agent_delegate = ToolInfo(
        name="agent_delegate",
        description=(
            "Delegate a complete, self-contained task to a specialized "
            "sub-agent. The sub-agent will execute independently and "
            "return its final result. Provide a fully detailed task "
            "description with all necessary context.\n\n"
            f"Available sub-agents:\n{chr(10).join(lines)}\n\n"
            "IMPORTANT: This tool blocks until the sub-agent finishes."
        ),
        parameters={
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Name of the sub-agent to delegate to",
                    "enum": names,
                },
                "task": {
                    "type": "string",
                    "description": (
                        "Complete self-contained task description for "
                        "the sub-agent. Include all necessary context, "
                        "file paths, and expected output."
                    ),
                },
            },
            "required": ["agent_name", "task"],
        },
        fn=_agent_delegate_fn,
    )

    agent.tools.register(agent_delegate)
