from textual.screen import Screen
from textual.containers import Vertical
from textual.widgets import Input, Label, Header, ListView
from textual.binding import Binding
from textual import on

from backend.tui.widgets.history import MessageHistory
from backend.tui.widgets.status_bar import StatusBar
from backend.tui.widgets.command_dropdown import CommandDropdown
from backend.tui.chat_handlers import ChatHandlerMixin

from backend.deps import get_llm_service, get_session_service


class ChatScreen(Screen, ChatHandlerMixin):
    BINDINGS = [
        Binding("ctrl+n", "new_session", "New"),
        Binding("escape", "handle_escape", "Cancel/Esc"),
    ]

    def __init__(self, load_session_id=None):
        super().__init__()
        self._load_session_id = load_session_id
        self._llm = get_llm_service()
        self._sess = get_session_service()
        self._session_id: str = ""
        self._streaming = False
        self._esc_pressed_at: float = 0.0
        self._last_usage: dict = {}
        self._cancel_hint: str = ""
        self._pending_messages: list[str] = []
        self._stream_worker = None

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
            StatusBar(f"model: {model_name} | / for help | {len(self._llm.tool_registry)} tools | Shift+Mouse to select | Ctrl+Q quit"),
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

    @on(Input.Changed)
    async def on_input_changed(self, event: Input.Changed):
        value = event.value
        dropdown = self.query_one("#command-dropdown", CommandDropdown)
        if value.startswith("/"):
            await dropdown.show_matches(value)
        else:
            await dropdown.hide_dropdown()

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

        self._stream_worker = self.run_worker(
            self._stream_response(content), exclusive=False,
        )
