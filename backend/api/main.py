import getpass
import os
import socket
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.deps import connect_services, disconnect_services, get_llm_service, get_mcp_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_services()

    llm = get_llm_service()
    mcp = get_mcp_service()
    current = llm.get_current_model()
    mcp_entries = llm.config.get("mcp_servers", [])
    external_tools = len(mcp.list_all_tools()) if mcp else 0
    port = os.environ.get("ILS4GAS_WEB_PORT", "8789")
    print(f"  tools: {len(llm.tool_registry)} built-in tools loaded")
    print(f"  model: {current['id']}")
    print(f"  mcp  : {len(mcp_entries)} external servers, {external_tools} external tools")
    print()
    print(f"  Local:   http://localhost:{port}")
    hostname = socket.gethostname()
    print(f"  Remote:  ssh -N -L {port}:localhost:{port} {getpass.getuser()}@{hostname}")
    print("           (set up SSH key first: ssh-copy-id user@server)")
    print(f"           Then open http://localhost:{port} in your local browser")

    yield

    await disconnect_services()


app = FastAPI(title="ILS4GAS", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
from backend.api.routes import chat, llm, session, mcp, skill, memory, ws

app.include_router(chat.router)
app.include_router(llm.router)
app.include_router(session.router)
app.include_router(mcp.router)
app.include_router(skill.router)
app.include_router(memory.router)
app.include_router(ws.router)

# Frontend static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def spa(full_path: str = ""):
        index = static_dir / "index.html"
        if index.exists():
            return HTMLResponse(
                content=index.read_text(encoding="utf-8"),
                headers={"Cache-Control": "no-cache"},
            )
        return HTMLResponse("<h1>Frontend not built. Run: cd frontend && npm install && npm run build</h1>")


def run_web(port: int = None, host: str = None):
    import uvicorn
    from backend.core.port import find_free_port

    p = port or int(os.getenv("ILS4GAS_WEB_PORT", "8789"))
    h = host or os.getenv("ILS4GAS_WEB_HOST", "0.0.0.0")
    actual = find_free_port(p, h)
    if actual != p:
        print(f"  port {p} in use, using {actual}")
    os.environ["ILS4GAS_WEB_PORT"] = str(actual)
    uvicorn.run("backend.api.main:app", host=h, port=actual, reload=False)


if __name__ == "__main__":
    run_web()
