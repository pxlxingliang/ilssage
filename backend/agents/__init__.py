from typing import Optional

from backend.core.agent import BaseAgent


def create_agent(
    behavior: str,
    *,
    system_prompt: Optional[str] = None,
) -> BaseAgent:
    """
    Create an agent with the given behavior.

    Args:
        behavior: "react" or "a2a"
        system_prompt: override the default system prompt

    Returns:
        A new BaseAgent instance
    """
    from backend.roles import get_role, list_roles

    if behavior == "react":
        from backend.agents.react_agent import ReActAgent

        capability, tool_factory = get_role("manager")
        manager_tools = tool_factory()
        prompt = system_prompt or capability.system_prompt
        return ReActAgent(manager_tools, prompt)

    if behavior == "a2a":
        from backend.agents.a2a_agent import A2AAgent

        mgr_cap, mgr_factory = get_role("manager")
        mgr_tools = mgr_factory()
        mgr_prompt = system_prompt or mgr_cap.system_prompt

        sub_agents = []
        for role_name in list_roles():
            if role_name == "manager":
                continue
            cap, tool_factory = get_role(role_name)
            sub_agents.append((cap, tool_factory()))

        return A2AAgent(mgr_tools, mgr_prompt, sub_agents)

    raise ValueError(f"Unknown behavior: {behavior}")
