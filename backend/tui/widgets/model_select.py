from textual.screen import Screen
from textual.containers import Vertical
from textual.widgets import Static, Header, ListView, ListItem, Label


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
