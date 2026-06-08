import os

port = int(os.environ.get("ILSSAGE_MCP_PORT", "50001"))
host = os.environ.get("ILSSAGE_MCP_HOST", "0.0.0.0")

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ILsSage", port=port, host=host)
