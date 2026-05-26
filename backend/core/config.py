import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


_DEFAULT_CONFIG_PATH = "~/.ilssage/config.json"


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    if path:
        candidate = Path(path).expanduser()
    else:
        candidate = Path(_DEFAULT_CONFIG_PATH).expanduser()

    if not candidate.exists():
        raise FileNotFoundError(
            f"Config not found at {candidate}.\n"
            f"Copy config.example.json to {candidate} and fill in your API keys."
        )

    with open(candidate, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Resolve environment variable references in apiKey fields
    return _resolve_env_refs(raw)


def _resolve_env_refs(obj: Any) -> Any:
    import re

    if isinstance(obj, dict):
        return {k: _resolve_env_refs(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_refs(i) for i in obj]
    if isinstance(obj, str):
        pattern = r"\$\{ENV:([^}]+)\}"
        match = re.fullmatch(pattern, obj)
        if match:
            return os.environ.get(match.group(1), "")
        return obj
    return obj
