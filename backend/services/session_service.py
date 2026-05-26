import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

DATA_ROOT = Path("~/.ilssage/data").expanduser()
SESSIONS_INDEX = DATA_ROOT / "sessions.json"
SESSIONS_DIR = DATA_ROOT / "sessions"


def _ensure_dirs():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> dict | list:
    if not path.exists():
        return {} if path.suffix == ".json" else []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(data, f, ensure_ascii=False, indent=2)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


class SessionService:
    def __init__(self):
        _ensure_dirs()

    # ── session CRUD ──────────────────────────────────────────

    def create_session(
        self, model_provider: str = "", model_name: str = "", title: str = ""
    ) -> Dict:
        sid = f"sess_{uuid4().hex[:12]}"
        now = _now()
        session = {
            "id": sid,
            "title": title or "New Chat",
            "created_at": now,
            "updated_at": now,
            "model_provider": model_provider,
            "model_name": model_name,
        }
        index = _read_json(SESSIONS_INDEX) if SESSIONS_INDEX.exists() else []
        index.append(session)
        _write_json(SESSIONS_INDEX, index)
        _write_json(SESSIONS_DIR / f"{sid}.json", [])
        return session

    def list_sessions(self, limit: int = 50) -> List[Dict]:
        if not SESSIONS_INDEX.exists():
            return []
        index = _read_json(SESSIONS_INDEX)
        index.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return index[:limit]

    def get_session(self, sid: str) -> Optional[Dict]:
        if not SESSIONS_INDEX.exists():
            return None
        for s in _read_json(SESSIONS_INDEX):
            if s["id"] == sid:
                return s
        return None

    def update_session(self, sid: str, **kwargs) -> Optional[Dict]:
        if not SESSIONS_INDEX.exists():
            return None
        index = _read_json(SESSIONS_INDEX)
        for s in index:
            if s["id"] == sid:
                s.update(kwargs)
                s["updated_at"] = _now()
                _write_json(SESSIONS_INDEX, index)
                return s
        return None

    def delete_session(self, sid: str) -> bool:
        if not SESSIONS_INDEX.exists():
            return False
        index = _read_json(SESSIONS_INDEX)
        new_index = [s for s in index if s["id"] != sid]
        if len(new_index) == len(index):
            return False
        _write_json(SESSIONS_INDEX, new_index)
        msg_file = SESSIONS_DIR / f"{sid}.json"
        if msg_file.exists():
            msg_file.unlink()
        return True

    # ── messages ──────────────────────────────────────────────

    def _msg_file(self, session_id: str, agent_name: Optional[str] = None) -> Path:
        if agent_name:
            return SESSIONS_DIR / f"{session_id}_sub_{agent_name}.json"
        return SESSIONS_DIR / f"{session_id}.json"

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List] = None,
        tool_call_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        agent_name: Optional[str] = None,
        reasoning_content: Optional[str] = None,
    ) -> Optional[Dict]:
        if not self.get_session(session_id):
            return None
        msg = {
            "id": f"msg_{uuid4().hex[:12]}",
            "role": role,
            "content": content,
            "tool_calls": tool_calls,
            "tool_call_id": tool_call_id,
            "reasoning_content": reasoning_content,
            "timestamp": _now(),
        }
        if metadata:
            msg["metadata"] = metadata
        msg_file = self._msg_file(session_id, agent_name)
        messages = _read_json(msg_file) if msg_file.exists() else []
        messages.append(msg)
        _write_json(msg_file, messages)
        self.update_session(session_id)
        return msg

    def get_messages(
        self, session_id: str, limit: int = 100, agent_name: Optional[str] = None
    ) -> List[Dict]:
        msg_file = self._msg_file(session_id, agent_name)
        if not msg_file.exists():
            return []
        messages = _read_json(msg_file)
        return messages[-limit:]

    def build_chat_history(
        self, session_id: str, limit: int = 100, agent_name: Optional[str] = None
    ) -> List[Dict]:
        """
        Build a chat history list suitable for LLM context.

        For DeepSeek thinking mode, messages with reasoning_content
        (including those with tool_calls but no content) are preserved,
        and reasoning_content is included in the output.

        Args:
            session_id: The session ID
            limit: Maximum number of messages to retrieve
            agent_name: Optional agent name for sub-sessions

        Returns:
            Filtered list of messages in OpenAI chat format
        """
        messages = self.get_messages(session_id, limit=limit, agent_name=agent_name)
        history = []
        for msg in messages:
            role = msg["role"]
            has_reasoning = bool(msg.get("reasoning_content"))
            if role == "assistant" and msg.get("tool_calls") and not (msg.get("content") or has_reasoning):
                continue
            entry: dict = {"role": role, "content": msg["content"]}
            if msg.get("tool_calls"):
                entry["tool_calls"] = msg["tool_calls"]
            if msg.get("tool_call_id"):
                entry["tool_call_id"] = msg["tool_call_id"]
            if has_reasoning:
                entry["reasoning_content"] = msg["reasoning_content"]
            history.append(entry)
        return history


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
