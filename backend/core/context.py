from pathlib import Path
from typing import Dict, Optional

WORKSPACE_DIR = Path("~/.ilssage/workspace").expanduser()

_DEFAULT_FILES: Dict[str, str] = {
    "AGENT.md": (
        "# Agent Behavior\n\n"
        "You are a helpful assistant. Follow these guidelines:\n"
        "- Answer questions accurately and concisely.\n"
        "- Use available tools when they help complete the task.\n"
        "- When you are unsure, ask clarifying questions.\n"
        "- When referencing local image files (plots, diagrams, screenshots) in "
        "your responses, use markdown image syntax with the file serving endpoint: "
        "`![description](/api/v1/files?path=/absolute/path/to/image.png)`.\n"
    ),
    "PERSONA.md": (
        "# Persona\n\n"
        "You are ILsSage, a professional AI assistant specialized in "
        "material science and computational chemistry related to Ionic Liquids.\n"
    ),
    "MEMORY.md": (
        "# Memory\n\n"
        "The user has not yet stored any long-term memories.\n"
    ),
}


class WorkspaceContext:

    def __init__(self):
        self._files = {
            "agent": WORKSPACE_DIR / "AGENT.md",
            "persona": WORKSPACE_DIR / "PERSONA.md",
            "memory": WORKSPACE_DIR / "MEMORY.md",
        }

    @classmethod
    def init_workspace(cls) -> None:
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        for name, content in _DEFAULT_FILES.items():
            path = WORKSPACE_DIR / name
            if name == "AGENT.md":
                path.write_text(content, encoding="utf-8")
            elif not path.exists():
                path.write_text(content, encoding="utf-8")

    def load_context(self) -> Dict[str, Optional[str]]:
        ctx: Dict[str, Optional[str]] = {}
        for key, path in self._files.items():
            if key == "agent":
                ctx[key] = _DEFAULT_FILES["AGENT.md"]
            elif path.exists():
                ctx[key] = path.read_text(encoding="utf-8")
            else:
                ctx[key] = None
        return ctx

    def build_system_prompt(self) -> str:
        ctx = self.load_context()
        parts: list[str] = []
        if ctx.get("persona"):
            parts.append(ctx["persona"])
        if ctx.get("agent"):
            parts.append(ctx["agent"])
        if ctx.get("memory"):
            parts.append(ctx["memory"])
        return "\n\n".join(parts)

    def read_file(self, name: str) -> Optional[str]:
        path = WORKSPACE_DIR / f"{name.upper()}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def write_file(self, name: str, content: str) -> None:
        path = WORKSPACE_DIR / f"{name.upper()}.md"
        path.write_text(content, encoding="utf-8")

    def append_memory(self, memory: str) -> None:
        path = self._files["memory"]
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        path.write_text(existing.rstrip() + f"\n- {memory}\n", encoding="utf-8")
