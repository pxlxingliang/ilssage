from backend.roles import AgentCapability
from backend.tools.builtin.bash import create_bash_tool
from backend.tools.builtin.glob import create_glob_tool
from backend.tools.builtin.grep import create_grep_tool
from backend.tools.builtin.read import create_read_tool
from backend.tools.builtin.write import create_write_tool
from backend.tools.registry import ToolRegistry

CAPABILITY = AgentCapability(
    name="hpc_task_manager",
    description=(
        "Submits computational tasks to HPC clusters and monitors job status. "
        "Use this agent when the user needs to run calculations on a remote "
        "high-performance computing cluster."
    ),
    tools=["bash", "read", "write", "glob", "grep"],
    system_prompt=(
        "You are an HPC task manager. Your responsibilities:\n"
        "1. Create job submission scripts for the target scheduler.\n"
        "2. Submit jobs to the cluster and monitor their status.\n"
        "3. Read job output and log files to extract results.\n"
        "4. Handle common errors (OOM, timeout, missing modules).\n\n"
        "When given a task:\n"
        "- First check what input files exist using glob.\n"
        "- Write an appropriate job script using write.\n"
        "- Submit the job and monitor until completion using bash.\n"
        "- Read output files to extract the requested results.\n"
        "- Return the results clearly."
    ),
    model_override=None,
)


def build_hpc_tools() -> ToolRegistry:
    registry = ToolRegistry()
    for factory in [
        create_read_tool,
        create_glob_tool,
        create_grep_tool,
        create_bash_tool,
        create_write_tool,
    ]:
        registry.register(factory())
    return registry
