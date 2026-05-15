import json
from rich.text import Text
from textual.widgets import Static, Collapsible
from textual.containers import VerticalScroll


class MessageHistory(VerticalScroll):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._msgs: list[dict] = []

    def add_message(self, role: str, content: str):
        self._msgs.append({"type": "message", "role": role, "content": content})
        prefix = self._prefix_for(role)
        self.mount(Static(Text.from_markup(prefix + content)))
        self.scroll_end(animate=False)

    def update_last(self, content: str):
        if self._msgs and self._msgs[-1]["type"] == "message" and self._msgs[-1]["role"] == "assistant":
            self._msgs[-1]["content"] = content
            for child in reversed(self.children):
                if isinstance(child, Static) and not isinstance(child, Collapsible):
                    prefix = self._prefix_for("assistant")
                    child.update(Text.from_markup(prefix + content))
                    self.scroll_end(animate=False)
                    return
            prefix = self._prefix_for("assistant")
            self.mount(Static(Text.from_markup(prefix + content)))
        else:
            self._msgs.append({"type": "message", "role": "assistant", "content": content})
            prefix = self._prefix_for("assistant")
            self.mount(Static(Text.from_markup(prefix + content)))
        self.scroll_end(animate=False)

    def add_tool_call(self, tool_name: str, args: str, result: str = ""):
        tc = {
            "type": "tool_call",
            "tool_name": tool_name,
            "args": args,
            "result": result,
        }
        self._msgs.append(tc)
        widget = self._make_tool_call_widget(tc)
        self.mount(widget)
        self.scroll_end(animate=False)

    def update_last_tool_result(self, result: str):
        for i in range(len(self._msgs) - 1, -1, -1):
            if self._msgs[i]["type"] == "tool_call":
                self._msgs[i]["result"] = result
                new_widget = self._make_tool_call_widget(self._msgs[i])
                for child in reversed(self.children):
                    if isinstance(child, Collapsible):
                        self.mount(new_widget, before=child)
                        child.remove()
                        self.scroll_end(animate=False)
                        return
                self.mount(new_widget)
                self.scroll_end(animate=False)
                return

    def clear(self):
        self._msgs.clear()
        self.remove_children()

    def _prefix_for(self, role: str) -> str:
        if role == "user":
            return "[bold blue]You:[/] "
        elif role == "system":
            return "[bold grey50]●[/] "
        else:
            return "[bold purple]AI:[/] "

    def _make_tool_call_widget(self, tc: dict) -> Collapsible:
        tool_name = tc["tool_name"]
        args = tc.get("args", "")
        result = tc.get("result", "")

        if result:
            icon = "🔧"
        else:
            icon = "⏳"

        title = f"{icon} {tool_name}"
        if args:
            preview = self._format_args_preview(args)
            if preview:
                title += f" ({preview})"
        if not result:
            title += " ..."

        lines = []
        if args:
            formatted = self._format_args_full(args)
            if formatted:
                lines.append(f"[bold]Arguments:[/]\n{formatted}")
        if result:
            if result.startswith("Error"):
                lines.append(f"[bold red]Result:[/] {result[:2000]}")
            else:
                lines.append(f"[bold]Result:[/] {result[:2000]}")

        content_text = "\n\n".join(lines) if lines else ""
        content = Static(Text.from_markup(content_text))
        return Collapsible(content, title=title)

    def _format_args_preview(self, args: str) -> str:
        if not args:
            return ""
        try:
            d = json.loads(args)
            parts = []
            for k, v in list(d.items())[:2]:
                sv = str(v)
                if len(sv) > 30:
                    sv = sv[:27] + "..."
                parts.append(f"{k}={sv}")
            preview = ", ".join(parts)
            if len(d) > 2:
                preview += ", ..."
            return preview
        except (json.JSONDecodeError, TypeError):
            preview = args[:60]
            if len(args) > 60:
                preview += "..."
            return preview

    def _format_args_full(self, args: str) -> str:
        if not args:
            return ""
        try:
            d = json.loads(args)
            return json.dumps(d, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            return args
