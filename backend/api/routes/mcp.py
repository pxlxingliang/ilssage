from fastapi import APIRouter, HTTPException

from backend.deps import get_mcp_service

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


@router.get("/servers")
async def list_servers():
    mcp = get_mcp_service()
    return {"servers": mcp.list_servers()}


@router.post("/servers/{name}/connect")
async def connect_server(name: str):
    mcp = get_mcp_service()
    error = await mcp.connect_server(name)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"connected": True, "name": name}


@router.post("/servers/{name}/disconnect")
async def disconnect_server(name: str):
    mcp = get_mcp_service()
    await mcp.disconnect_server(name)
    return {"disconnected": True, "name": name}


@router.get("/tools")
async def list_tools():
    mcp = get_mcp_service()
    return {"tools": mcp.list_all_tools()}


@router.get("/tools/{name}")
async def get_tool(name: str):
    mcp = get_mcp_service()
    tool = mcp.get_tool(name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.post("/tools/{name}/execute")
async def execute_tool(name: str, data: dict = None):
    mcp = get_mcp_service()
    args = (data or {}).get("arguments", {})
    result = await mcp.execute_tool(name, args)
    return {"result": result}
