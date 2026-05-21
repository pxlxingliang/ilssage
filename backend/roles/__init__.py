"""
Agent role definitions.

Each role module defines:
  - CAPABILITY: AgentCapability (name, description, tools list, system_prompt)
  - build_xxx_tools() -> ToolRegistry: builds the tool set for this role

To add a new role:
  1. Create a new .py file in this directory
  2. Add it to _register_roles() below
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class AgentCapability:
    name: str
    description: str
    tools: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    system_prompt: str = ""
    model_override: Optional[str] = None


AgentFactory = Callable[[], object]

RoleEntry = Tuple[AgentCapability, AgentFactory]

_roles: Dict[str, RoleEntry] = {}


def _register_role(
    capability: AgentCapability, factory: AgentFactory
) -> None:
    _roles[capability.name] = (capability, factory)


def get_role(name: str) -> RoleEntry:
    return _roles[name]


def list_roles() -> List[str]:
    return list(_roles.keys())


def _register_roles() -> None:
    from backend.roles.manager import (
        CAPABILITY as MGR_CAP,
        build_manager_tools,
    )
    from backend.roles.hpc_agent import (
        CAPABILITY as HPC_CAP,
        build_hpc_tools,
    )

    _register_role(MGR_CAP, build_manager_tools)
    _register_role(HPC_CAP, build_hpc_tools)


_register_roles()
