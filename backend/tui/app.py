from textual.app import App
from backend.tui.screen import ChatScreen


class IlsSageApp(App):
    def __init__(self, session_id=None, **kwargs):
        super().__init__(**kwargs)
        self._session_arg = session_id
        self.session_id = None

    def action_quit(self):
        screen = self.screen
        if hasattr(screen, '_session_id'):
            self.session_id = screen._session_id
        self.exit()

    async def on_mount(self):
        from backend.deps import connect_services, get_llm_service, get_mcp_service

        await connect_services()

        llm = get_llm_service()
        mcp = get_mcp_service()
        current = llm.get_current_model()
        mcp_entries = llm.config.get("mcp_servers", [])
        external_tools = len(mcp.list_all_tools()) if mcp else 0
        print(f"  tools: {len(llm.tool_registry)} built-in tools loaded")
        print(f"  model: {current['id']}")
        print(f"  mcp  : {len(mcp_entries)} external servers, {external_tools} external tools")

        self.push_screen(ChatScreen(load_session_id=self._session_arg))

    CSS = """
    Screen {
        background: #ffffff;
        color: #1a1a2e;
    }
    Header {
        background: #f0f0f5;
        color: #1a1a2e;
    }
    #history {
        height: 1fr;
    }
    #bottom-bar {
        height: auto;
    }
    Input {
        background: #f7f7f8;
        color: #1a1a2e;
        border: solid #e5e7eb;
    }
    Input:focus {
        border: solid #6366f1;
    }
    StatusBar {
        background: #f0f0f5;
        color: #6b7280;
    }
    #thinking {
        color: #6366f1;
    }
    #history Collapsible {
        border: solid #c7d2fe;
        margin: 1 0;
    }
    #history Collapsible:focus-within {
        border: solid #6366f1;
    }
    #history CollapsibleTitle {
        color: #4f46e5;
    }
    #history CollapsibleTitle:hover {
        background: #eef2ff;
    }
    #history Contents {
        background: #f5f3ff;
    }
    ListView {
        background: #ffffff;
        color: #1a1a2e;
    }
    ListView > ListItem {
        background: #ffffff;
        color: #1a1a2e;
        padding: 1;
    }
    ListView > ListItem:hover {
        background: #eef2ff;
    }
    ListView > ListItem.--highlight {
        background: #e0e7ff;
    }
    #command-dropdown {
        background: #ffffff;
        border: solid #6366f1;
        height: auto;
        max-height: 8;
    }
    #command-dropdown > ListItem {
        background: #ffffff;
        color: #1a1a2e;
        padding: 0 1;
    }
    #command-dropdown > ListItem:hover {
        background: #eef2ff;
    }
    #command-dropdown > ListItem.--highlight {
        background: #e0e7ff;
        color: #6366f1;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
    ]

    def on_mount(self):
        self.push_screen(ChatScreen(load_session_id=self._session_arg))
