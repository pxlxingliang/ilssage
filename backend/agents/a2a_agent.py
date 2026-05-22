from typing import AsyncIterator, Dict, List, Optional, Tuple

from loguru import logger

from backend.agents.react_agent import ReActAgent
from backend.core.events import AgentEvent
from backend.roles import AgentCapability
from backend.tools.registry import ToolInfo, ToolRegistry


class A2AAgent(ReActAgent):

    def __init__(
        self,
        tools: Optional[ToolRegistry] = None,
        system_prompt: Optional[str] = None,
        sub_agents: Optional[List[Tuple[AgentCapability, ToolRegistry]]] = None,
    ):
        super().__init__(tools, system_prompt)
        self._sub_agents: List[Tuple[AgentCapability, ToolRegistry]] = sub_agents or []
        self._sub_agents_registered = False

    def _register_sub_agent_tools(self, session_id: str) -> None:
        if self._sub_agents_registered:
            return
        self._sub_agents_registered = True

        from backend.deps import get_llm_service, get_session_service

        sess = get_session_service()

        for capability, sub_tools in self._sub_agents:
            self._register_one_sub_agent(sess, capability, sub_tools, session_id)

    def _register_one_sub_agent(
        self, sess, capability: AgentCapability, sub_tools: ToolRegistry, session_id: str
    ) -> None:
        cap = capability
        tools = sub_tools
        sid = session_id

        async def delegate_fn(task: str) -> str:
            messages = sess.get_messages(sid, agent_name=cap.name)
            if not messages:
                messages = [{"role": "system", "content": cap.system_prompt}]

            sess.add_message(sid, "user", task, agent_name=cap.name)

            from backend.deps import get_llm_service
            from backend.agents.react_agent import ReActAgent as SubReActAgent

            llm = get_llm_service()
            if cap.model_override:
                provider = llm.get_provider(cap.model_override)
            else:
                provider = llm.get_provider()

            sub_agent = SubReActAgent(tools, cap.system_prompt)

            try:
                result = await sub_agent.run(messages, provider, session_id=sid)
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                result = f"Sub-agent '{cap.name}' failed: {error_msg}"
                logger.warning(f"Sub-agent '{cap.name}' failed: {e}")

            sess.add_message(sid, "assistant", result, agent_name=cap.name)
            return result

        tool_info = ToolInfo(
            name=f"delegate_{cap.name}",
            description=(
                f"Delegate a task to the '{cap.name}' sub-agent. "
                f"{cap.description}"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": (
                            "Complete self-contained task description for "
                            f"the {cap.name} sub-agent. Include all "
                            "necessary context, file paths, and expected output."
                        ),
                    },
                },
                "required": ["task"],
            },
            fn=delegate_fn,
        )

        self.tools.register(tool_info)
        logger.info(f"Registered sub-agent delegate tool: delegate_{cap.name}")

    async def run(
        self,
        messages: List[Dict],
        provider,
        session_id: Optional[str] = None,
    ) -> str:
        if session_id and self._sub_agents:
            self._register_sub_agent_tools(session_id)
        return await super().run(messages, provider, session_id)

    async def stream_run(
        self,
        messages: List[Dict],
        provider,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[AgentEvent]:
        if session_id and self._sub_agents:
            self._register_sub_agent_tools(session_id)
        async for event in super().stream_run(messages, provider, session_id):
            yield event
