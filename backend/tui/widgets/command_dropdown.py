from textual.widgets import ListView, ListItem, Label

from backend.tui.constants import COMMAND_DESCRIPTIONS


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
