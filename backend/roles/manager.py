from backend.roles import AgentCapability
from backend.tools.builtin import register_builtin_tools
from backend.tools.loader import load_tools_from_mcp_modules
from backend.tools.registry import ToolRegistry

CAPABILITY = AgentCapability(
    name="manager",
    description=(
        "General-purpose assistant. Handles file operations, code editing, "
        "web search, shell commands, and skill loading. Can delegate to "
        "specialized sub-agents when needed."
    ),
    tools=[],
    system_prompt=(
        "You are a helpful assistant. Follow these guidelines:\n"
        "- Answer questions accurately and concisely.\n"
        "- Use available tools when they help complete the task.\n"
        "- When you are unsure, ask clarifying questions.\n"
        "- For complex computational tasks, consider delegating to "
        "hpc_task_manager."
    ),
    model_override=None,
)


def build_manager_tools() -> ToolRegistry:
    registry = load_tools_from_mcp_modules()
    registry.extend(register_builtin_tools())
    return registry
