import time

from textual.widgets import ListView, Input, Label

from backend.core.context import WorkspaceContext
from backend.core.events import AgentEventType
from backend.core.token_counter import count_tokens
from backend.services.chat_service import stream_chat
from backend.tui.widgets.history import MessageHistory
from backend.tui.widgets.status_bar import StatusBar
from backend.tui.widgets.model_select import ModelSelectScreen
from backend.tui.constants import get_help_text


class ChatHandlerMixin:
    """Mixin for ChatScreen command handling and streaming logic."""

    _llm = None
    _sess = None
    _agent_factory = None
    _session_id = ""
    _streaming = False
    _esc_pressed_at = 0.0
    _last_usage = {}
    _cancel_hint = ""
    _pending_messages = []
    _stream_worker = None

    def _handle_command(self, cmd: str):
        history = self.query_one("#history", MessageHistory)
        parts = cmd.split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd in ("/exit", "/quit"):
            history.add_message("system", "Goodbye!")
            self.app.session_id = self._session_id
            self.app.exit()

        elif cmd == "/help":
            history.add_message("system", get_help_text())

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

    async def action_handle_escape(self):
        dropdown = self.query_one("#command-dropdown", ListView)
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
            if self._stream_worker:
                self._stream_worker.cancel()
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
        parts.append(f"/ for commands | {len(self._llm.tool_registry)} tools")
        status = self.query_one(StatusBar)
        status.update(" | ".join(parts))

    async def _stream_response(self, user_content: str):
        history = self.query_one("#history", MessageHistory)
        thinking = self.query_one("#thinking", Label)

        thinking.update("thinking...")
        self._streaming = True
        self._last_usage = {}
        self._cancel_hint = ""
        self._esc_pressed_at = 0.0

        system_prompt = WorkspaceContext().build_system_prompt()
        messages = self._sess.build_chat_history(self._session_id)
        messages.append({"role": "user", "content": user_content})
        system_messages = [{"role": "system", "content": system_prompt}]
        full_for_count = system_messages + messages
        model_id = self._llm.current_model or ""
        model_name = model_id.split("/", 1)[1] if "/" in model_id else model_id
        prompt_tokens = count_tokens(full_for_count, model_name)
        context_limit = self._llm.get_current_model().get("limit", {}).get("context", 128000)
        self._update_status(f"tokens: {prompt_tokens:,}/{context_limit // 1000}K")

        segment_accumulated = ""

        try:
            async for event in stream_chat(self._session_id, user_content):
                if event.type == AgentEventType.CONTENT_CHUNK:
                    segment_accumulated += event.data["text"]
                    history.update_last(segment_accumulated)

                elif event.type == AgentEventType.TOOL_CALL_START:
                    tool_name = event.data.get("tool_name", "?")
                    segment_accumulated = ""
                    history.add_tool_call(tool_name, event.data.get("args", ""))
                    thinking.update(f"calling {tool_name}...")

                elif event.type == AgentEventType.TOOL_CALL_END:
                    history.update_last_tool_result(event.data.get("result", ""))
                    thinking.update("thinking...")

                elif event.type == AgentEventType.ERROR:
                    history.add_message("system", f"Error: {event.data.get('message', 'unknown')}")

                elif event.type == AgentEventType.DONE:
                    usage = event.data.get("usage", {})
                    if usage:
                        p = usage.get("prompt_tokens", 0)
                        c = usage.get("completion_tokens", 0)
                        t = usage.get("total_tokens", 0)
                        self._update_status(f"tokens: {p:,} prompt + {c:,} completion = {t:,}")
                        self._last_usage = usage

        except Exception as e:
            history.add_message("system", f"Error: {e}")

        thinking.update("")
        self._streaming = False
        self._stream_worker = None

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
