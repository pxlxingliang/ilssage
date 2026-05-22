from backend.services.llm_service import LLMService
from backend.services.session_service import SessionService
from backend.services.mcp_service import MCPService

_llm_service: LLMService = None  # type: ignore
_session_service: SessionService = None  # type: ignore
_mcp_service: MCPService = None  # type: ignore
_behavior: str = "react"

_BOOTSTRAPPED = False


def bootstrap(behavior: str = "react"):
    global _BOOTSTRAPPED, _llm_service, _session_service, _behavior, _mcp_service
    if _BOOTSTRAPPED:
        return
    _BOOTSTRAPPED = True

    from backend.core.context import WorkspaceContext
    from backend.roles.manager import build_manager_tools

    WorkspaceContext.init_workspace()

    _llm_service = LLMService()
    _llm_service.tool_registry = build_manager_tools()

    _session_service = SessionService()
    _behavior = behavior

    mcp_entries = _llm_service.config.get("mcp_servers", [])
    _mcp_service = MCPService.from_config_entries(mcp_entries)


async def connect_services():
    if _mcp_service:
        await _mcp_service.connect_all()


async def disconnect_services():
    if _mcp_service:
        await _mcp_service.disconnect_all()


def get_llm_service() -> LLMService:
    return _llm_service


def get_session_service() -> SessionService:
    return _session_service


def get_mcp_service() -> MCPService:
    return _mcp_service


def set_mcp_service(service: MCPService):
    global _mcp_service
    _mcp_service = service


def get_behavior() -> str:
    return _behavior
