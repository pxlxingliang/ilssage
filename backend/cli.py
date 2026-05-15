import argparse
import sys
from backend.core.env import EnvManager


def main():
    EnvManager.init()

    parser = argparse.ArgumentParser(prog="ils4gas")
    parser.add_argument("--version", action="store_true", help="Print version")
    parser.add_argument("--session", "-s", type=str, default=None, help="Load a specific session on startup (TUI mode)")
    sub = parser.add_subparsers(dest="mode", title="modes")

    # ---- Web mode ----
    web = sub.add_parser("web", help="Start web UI server")
    web.add_argument("--port", type=int, default=None, help="Web server port")
    web.add_argument("--host", type=str, default=None, help="Web server host")

    # ---- MCP mode ----
    mcp = sub.add_parser("mcp", help="Start MCP server")
    mcp.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse", "streamable-http"],
        default=None,
        help="Transport protocol",
    )
    mcp.add_argument("--port", type=int, default=None, help="MCP server port")
    mcp.add_argument("--host", type=str, default=None, help="MCP server host")

    args = parser.parse_args()

    if args.version:
        from importlib.metadata import version
        print(f"ILS4GAS v{version('ils4gas')}")
        return

    if args.mode == "web":
        from backend.main import run_web
        run_web(port=args.port, host=args.host)
    elif args.mode == "mcp":
        from backend.mcp_server.server import run_mcp
        run_mcp(
            transport=args.transport,
            port=args.port,
            host=args.host,
        )
    else:
        # Default: TUI mode
        from backend.tui.cli import run_tui
        run_tui(session_id=args.session)


if __name__ == "__main__":
    main()
