import os
from importlib.metadata import version


def _load_tools():
    from pathlib import Path
    import importlib

    module_dir = Path(__file__).parent / "modules"

    for py_file in module_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        module_name = f"backend.mcp_server.modules.{py_file.stem}"
        try:
            importlib.import_module(module_name)
            print(f"loaded: {module_name}")
        except Exception as e:
            print(f"failed to load {module_name}: {e}")


def run_mcp(transport: str = None, port: int = None, host: str = None):
    print(f"IlsSage v{version('ilssage')}")

    if transport:
        os.environ["ILSSAGE_MCP_TRANSPORT"] = transport
    if host:
        os.environ["ILSSAGE_MCP_HOST"] = host

    _load_tools()

    from backend.mcp_server import mcp
    from backend.core.port import find_free_port

    t = os.environ.get("ILSSAGE_MCP_TRANSPORT", "stdio")
    h = os.environ.get("ILSSAGE_MCP_HOST", "localhost")
    requested = port or int(os.environ.get("ILSSAGE_MCP_PORT", "50001"))

    actual = requested
    if t != "stdio":
        actual = find_free_port(requested, h)
        if actual != requested:
            print(f"  port {requested} in use, using {actual}")
            os.environ["ILSSAGE_MCP_PORT"] = str(actual)
    else:
        os.environ["ILSSAGE_MCP_PORT"] = str(requested)

    if t == "stdio":
        print("Starting IlsSage MCP server (stdio)...")
    else:
        print(f"Starting IlsSage MCP server at {h}:{actual} ({t})...")

    mcp.run(transport=t)
