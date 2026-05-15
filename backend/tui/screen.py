import time
from textual.screen import Screen
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Input, Label, Header, ListView, ListItem
from textual.binding import Binding
from textual import on

from backend.tui.widgets.history import MessageHistory
from backend.tui.widgets.status_bar import StatusBar

from backend.agents.react_agent import ReActAgent
from backend.services.llm_service import LLMService
from backend.services.session_service import SessionService
from backend.tools.loader import load_tools_from_mcp_modules
from backend.tools.builtin import register_builtin_tools
from backend.core.context import WorkspaceContext
from backend.core.events import AgentEventType
from backend.core.token_counter import count_tokens, estimate_text_tokens
from backend.services.title_service import generate_title

COMMAND_DESCRIPTIONS = {
    "/exit": "Exit ILS4GAS",
    "/quit": "Exit ILS4GAS",
    "/model": "Switch LLM model",
    "/help": "Show available commands",
    "/clear": "Start a new session",
    "/new": "Start a new session",
}


class ModelSelectScreen(Screen):
    def __init__(self, models: list[dict], callback):
        super().__init__()
        self._models = models
        self._callback = callback
        self._id_map: dict[str, str] = {}

    def compose(self):
        items = []
        for m in self._models:
            safe_id = m["id"].replace("/", "_").replace(".", "_")
            self._id_map[safe_id] = m["id"]
            items.append(ListItem(Label(f"{m['name']}  ({m['provider']})"), id=safe_id))
        self._list = ListView(*items)
        yield Header()
        yield Vertical(
            Static("Select a model (Enter to confirm, Esc to cancel):"),
            self._list,
        )

    def on_list_view_selected(self, event: ListView.Selected):
        if event.item and event.item.id:
            real_id = self._id_map.get(event.item.id, event.item.id)
            self._callback(real_id)
            self.app.pop_screen()

    def on_screen_resume(self):
        self._list.focus()


class CommandDropdown(ListView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.can_focus = True
        self.display = False

    async def show_matches(self, prefix: str):
        prefix = prefix.strip().lower()
        await self.clear()
        if not prefix.startswith("/"):
            self.display = False
            return
        matches = [
            (cmd, desc)
            for cmd, desc in COMMAND_DESCRIPTIONS.items()
            if cmd.startswith(prefix)
        ]
        if matches:
            items = [
                ListItem(Label(f"{cmd}  ({desc})"), id="cmd_" + cmd.lstrip("/"))
                for cmd, desc in matches
            ]
            await self.extend(items)
            self.display = True
        else:
            self.display = False

    async def hide_dropdown(self):
        self.display = False
        await self.clear()


class ChatScreen(Screen):
    BINDINGS = [
        Binding("ctrl+n", "new_session", "New"),
        Binding("escape", "handle_escape", "Cancel/Esc"),
    ]

    def __init__(self, load_session_id=None):
        super().__init__()
        self._load_session_id = load_session_id
        self._llm = LLMService()
        self._sess = SessionService()
        self._tool_registry = load_tools_from_mcp_modules()
        self._tool_registry.extend(register_builtin_tools())
        self._llm.tool_registry = self._tool_registry
        self._session_id: str = ""
        self._agent = None
        self._streaming = False
        self._esc_pressed_at: float = 0.0
        self._last_usage: dict = {}
        self._cancel_hint: str = ""
        self._pending_messages: list[str] = []

    def _make_agent(self):
        system_prompt = WorkspaceContext().build_system_prompt()
        return ReActAgent(
            llm_service=self._llm,
            tool_registry=self._tool_registry,
            system_prompt=system_prompt,
        )

    def compose(self):
        if self._load_session_id and self._sess.get_session(self._load_session_id):
            self._session_id = self._load_session_id
        else:
            sess = self._sess.create_session(
                model_provider=self._llm.get_current_model().get("provider", ""),
                model_name=self._llm.get_current_model().get("id", ""),
            )
            self._session_id = sess["id"]
        model_name = self._llm.get_current_model().get("name", "?")
        yield Header()
        yield MessageHistory(id="history")
        yield Vertical(
            Input(placeholder="Type a message... (Enter to send, / for commands)", id="chat-input"),
            CommandDropdown(id="command-dropdown"),
            Label("", id="thinking"),
            StatusBar(f"model: {model_name} | / for help | {len(self._tool_registry)} tools | Shift+Mouse to select | Ctrl+Q quit"),
            id="bottom-bar",
        )

    def on_mount(self):
        self.query_one("#chat-input", Input).focus()
        if self._load_session_id and self._session_id == self._load_session_id:
            history = self.query_one("#history", MessageHistory)
            msgs = self._sess.get_messages(self._session_id)
            i = 0
            while i < len(msgs):
                msg = msgs[i]
                role = msg["role"]
                content = msg["content"]
                if role == "tool":
                    i += 1
                    continue
                if role == "assistant" and msg.get("tool_calls"):
                    if content:
                        history.add_message(role, content)
                    for tc in msg["tool_calls"]:
                        tc_name = tc.get("function", {}).get("name", "?")
                        tc_args = tc.get("function", {}).get("arguments", "")
                        tc_id = tc.get("id", "")
                        tc_result = ""
                        for j in range(i + 1, len(msgs)):
                            if msgs[j]["role"] == "tool" and msgs[j].get("tool_call_id") == tc_id:
                                tc_result = msgs[j]["content"]
                                break
                        history.add_tool_call(tc_name, tc_args, tc_result)
                    i += 1
                    continue
                history.add_message(role, content)
                i += 1

    # ── command dropdown ──────────────────────────────────

    @on(Input.Changed)
    async def on_input_changed(self, event: Input.Changed):
        value = event.value
        dropdown = self.query_one("#command-dropdown", CommandDropdown)
        if value.startswith("/"):
            await dropdown.show_matches(value)
        else:
            await dropdown.hide_dropdown()

    async def action_handle_escape(self):
        dropdown = self.query_one("#command-dropdown", CommandDropdown)
        if dropdown.display:
            await dropdown.hide_dropdown()
            self.query_one("#chat-input", Input).focus()
            return

        if not self._streaming:
            return

        now = time.monotonic()
        if self._esc_pressed_at and (now - self._esc_pressed_at) < 1.5:
            self._esc_pressed_at = 0.0
            self._cancel_hint = ""
            self._update_status()
            if self._agent:
                self._agent.cancel()
            return

        self._esc_pressed_at = now
        self._cancel_hint = "Press Esc again to stop"
        self._update_status()
        self.set_timer(1.5, self._reset_esc)

    def _reset_esc(self):
        self._esc_pressed_at = 0.0
        self._cancel_hint = ""
        if self._streaming:
            self._update_status()

    def _update_status(self, token_info: str = ""):
        model_name = self._llm.get_current_model().get("name", "?")
        context_limit = self._llm.get_current_model().get("limit", {}).get("context", 128000)
        parts = [
            f"model: {model_name}",
        ]
        if self._cancel_hint:
            parts.append(self._cancel_hint)
        elif token_info:
            parts.append(token_info)
        else:
            parts.append(f"limit: {context_limit // 1000}K")
        parts.append(f"/ for commands | {len(self._tool_registry)} tools")
        status = self.query_one(StatusBar)
        status.update(" | ".join(parts))

    def action_new_session(self):
        history = self.query_one("#history", MessageHistory)
        history.add_message("system", "Starting new session...")
        sess = self._sess.create_session(
            model_provider=self._llm.get_current_model().get("provider", ""),
            model_name=self._llm.get_current_model().get("id", ""),
        )
        self._session_id = sess["id"]
        history.clear()
        self._update_status()

    @on(ListView.Selected)
    async def on_command_selected(self, event: ListView.Selected):
        if event.control.id == "command-dropdown" and event.item:
            safe_id = event.item.id
            cmd = "/" + safe_id[4:]
            input_widget = self.query_one("#chat-input", Input)
            input_widget.value = cmd + " "
            input_widget.cursor_position = len(cmd) + 1
            await self.query_one("#command-dropdown", CommandDropdown).hide_dropdown()
            input_widget.focus()
            event.stop()

    # ── chat input ────────────────────────────────────────

    async def on_input_submitted(self, event: Input.Submitted):
        content = event.value.strip()
        if not content:
            return

        input_widget = self.query_one("#chat-input", Input)
        input_widget.clear()
        await self.query_one("#command-dropdown", CommandDropdown).hide_dropdown()

        if content.startswith("/"):
            self._handle_command(content)
            input_widget.focus()
            return

        history = self.query_one("#history", MessageHistory)
        history.add_message("user", content)

        if self._streaming:
            self._pending_messages.append(content)
            count = len(self._pending_messages)
            self._update_status(f"{count} task(s) queued...")
            return

        self.run_worker(self._stream_response(content), exclusive=False)

    # ── commands ──────────────────────────────────────────

    def _handle_command(self, cmd: str):
        history = self.query_one("#history", MessageHistory)
        parts = cmd.split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd in ("/exit", "/quit"):
            history.add_message("system", "Goodbye!")
            self.app.session_id = self._session_id
            self.app.exit()

        elif cmd == "/help":
            help_text = (
                "Commands:\n"
                "  /exit, /quit    Exit ILS4GAS\n"
                "  /model          Switch LLM model\n"
                "  /clear, /new    Start a new session\n"
                "  /help           Show this help\n"
                "\n"
                "Tips:\n"
                "  Shift+Mouse drag to select and copy text\n"
                "  Esc    Cancel streaming (press twice quickly)"
            )
            history.add_message("system", help_text)

        elif cmd in ("/clear", "/new"):
            self.action_new_session()

        elif cmd == "/model":
            self._show_model_selector()

        else:
            history.add_message("system", f"Unknown command: {cmd}.  Type /help for commands.")

    def _show_model_selector(self):
        models = self._llm.list_models()

        def on_model_selected(model_id: str):
            self._llm.switch_model(model_id)
            info = self._llm.get_current_model()
            history = self.query_one("#history", MessageHistory)
            history.add_message("system", f"Switched to {info['name']} ({info['id']})")
            self._update_status()

        self.app.push_screen(ModelSelectScreen(models, on_model_selected))

    async def _auto_title(self, user_content: str):
        session = self._sess.get_session(self._session_id)
        if not session or session.get("title") != "New Chat":
            return
        try:
            title = await generate_title(user_content, self._llm)
            if title:
                self._sess.update_session(self._session_id, title=title)
        except Exception:
            pass

    # ── streaming via ReActAgent ──────────────────────────

    async def _stream_response(self, user_content: str):
        history = self.query_one("#history", MessageHistory)
        thinking = self.query_one("#thinking", Label)

        thinking.update("thinking...")
        self._sess.add_message(self._session_id, "user", user_content)
        self._streaming = True
        self._last_usage = {}
        self._cancel_hint = ""
        self._esc_pressed_at = 0.0

        messages = []
        for msg in self._sess.get_messages(self._session_id)[:-1]:
            role = msg["role"]
            if role == "tool":
                continue
            if role == "assistant" and msg.get("tool_calls") and not msg.get("content"):
                continue
            entry = {"role": role, "content": msg["content"]}
            if msg.get("tool_calls"):
                entry["tool_calls"] = msg["tool_calls"]
            if msg.get("tool_call_id"):
                entry["tool_call_id"] = msg["tool_call_id"]
            messages.append(entry)
        messages.append({"role": "user", "content": user_content})

        agent = self._make_agent()
        self._agent = agent
        system_messages = [{"role": "system", "content": agent.system_prompt}]
        full_for_count = system_messages + messages
        model_id = self._llm.current_model or ""
        model_name = model_id.split("/", 1)[1] if "/" in model_id else model_id
        prompt_tokens = count_tokens(full_for_count, model_name)
        context_limit = self._llm.get_current_model().get("limit", {}).get("context", 128000)
        self._update_status(f"tokens: {prompt_tokens:,}/{context_limit // 1000}K")

        accumulated = ""
        segment_accumulated = ""
        tool_calls: list[dict] = []
        done_received = False

        try:
            async for event in agent.stream_run(messages):
                if event.type == AgentEventType.CONTENT_CHUNK:
                    accumulated += event.data["text"]
                    segment_accumulated += event.data["text"]
                    history.update_last(segment_accumulated)

                elif event.type == AgentEventType.TOOL_CALL_START:
                    tool_name = event.data.get("tool_name", "?")
                    tc_id = event.data.get("tool_call_id", "")
                    tool_calls.append({
                        "id": tc_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": event.data.get("args", ""),
                        },
                    })
                    segment_accumulated = ""
                    history.add_tool_call(tool_name, event.data.get("args", ""))
                    thinking.update(f"calling {tool_name}...")

                elif event.type == AgentEventType.TOOL_CALL_END:
                    if tool_calls:
                        tool_calls[-1]["_result"] = event.data.get("result", "")
                    history.update_last_tool_result(event.data.get("result", ""))
                    thinking.update("thinking...")

                elif event.type == AgentEventType.ERROR:
                    history.add_message("system", f"Error: {event.data.get('message', 'unknown')}")

                elif event.type == AgentEventType.DONE:
                    done_received = True
                    usage = event.data.get("usage", {})
                    if usage:
                        p = usage.get("prompt_tokens", 0)
                        c = usage.get("completion_tokens", 0)
                        t = usage.get("total_tokens", 0)
                        self._update_status(f"tokens: {p:,} prompt + {c:,} completion = {t:,}")
                        self._last_usage = usage
        except Exception as e:
            history.add_message("system", f"Error: {e}")

        if accumulated:
            content = accumulated
            if not done_received:
                content += "\n\n*(Output truncated by user)*"
            saved_calls = [
                {k: v for k, v in tc.items() if k != "_result"}
                for tc in tool_calls
            ] if tool_calls else None
            metadata = None
            if self._last_usage:
                metadata = {"token_usage": self._last_usage}
            self._sess.add_message(
                self._session_id, "assistant", content,
                tool_calls=saved_calls,
                metadata=metadata,
            )
            for tc in tool_calls:
                if "_result" in tc:
                    self._sess.add_message(
                        self._session_id, "tool", tc["_result"],
                        tool_call_id=tc["id"],
                    )
            self.run_worker(
                self._auto_title(user_content),
                exclusive=False,
            )

        thinking.update("")
        self._streaming = False
        self._agent = None

        if self._pending_messages:
            next_content = self._pending_messages.pop(0)
            self.run_worker(self._stream_response(next_content), exclusive=False)
            count = len(self._pending_messages)
            if count:
                self._update_status(f"{count} task(s) queued...")
            else:
                self._update_status()
        else:
            self._update_status()
