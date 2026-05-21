from typing import Optional

from backend.core.agent import BaseAgent


def create_agent(
    behavior: str,
    provider,
    *,
    session_service=None,
    system_prompt: Optional[str] = None,
) -> BaseAgent:
    """
    Create an agent with the given behavior.

    Args:
        behavior: "react" or "a2a"
        provider: LLMProvider instance for API calls
        session_service: required for "a2a" behavior (sub-agent persistence)
        system_prompt: override the default system prompt

    Returns:
        A new BaseAgent instance
    """
    from backend.roles import get_role

    if behavior == "react":
        from backend.agents.react_agent import ReActAgent

        capability, tool_factory = get_role("manager")
        manager_tools = tool_factory()
        prompt = system_prompt or capability.system_prompt
        return ReActAgent(provider, manager_tools, prompt)

    if behavior == "a2a":
        from backend.agents.a2a_agent import (
            SubAgentManager,
            add_agent_delegate_tool,
        )
        from backend.agents.react_agent import ReActAgent

        mgr_cap, mgr_factory = get_role("manager")
        mgr_tools = mgr_factory()
        mgr_prompt = system_prompt or mgr_cap.system_prompt
        manager_agent = ReActAgent(provider, mgr_tools, mgr_prompt)

        hpc_cap, hpc_factory = get_role("hpc_task_manager")
        hpc_tools = hpc_factory()

        sub_mgr = SubAgentManager(session_service)
        sub_mgr.register(hpc_cap, hpc_tools)

        add_agent_delegate_tool(manager_agent, sub_mgr)

        return manager_agent

    raise ValueError(f"Unknown behavior: {behavior}")
