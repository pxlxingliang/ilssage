import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.deps import get_session_service
from backend.services.chat_service import stream_chat

router = APIRouter()


@router.websocket("/api/v1/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    sess = get_session_service()
    _stream_task: asyncio.Task | None = None
    _current_session_id: str | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")

            if msg_type == "history":
                sid = data.get("session_id", "")
                if sess.get_session(sid):
                    msgs = sess.get_messages(sid)
                else:
                    msgs = []
                await websocket.send_json({
                    "type": "history",
                    "session_id": sid,
                    "messages": msgs,
                })

            elif msg_type == "cancel":
                if _stream_task and not _stream_task.done():
                    _stream_task.cancel()
                await websocket.send_json({
                    "type": "done",
                    "cancelled": True,
                    "session_id": _current_session_id,
                })

            elif msg_type == "send":
                content = data.get("content", "")
                if not content:
                    continue

                session_id = data.get("session_id", "")
                if not session_id or not sess.get_session(session_id):
                    session = sess.create_session()
                    session_id = session["id"]
                    await websocket.send_json({
                        "type": "session_created",
                        "session_id": session_id,
                    })

                _current_session_id = session_id

                async def _run_stream():
                    try:
                        async for event in stream_chat(session_id, content):
                            await websocket.send_json(event.to_dict())
                    except asyncio.CancelledError:
                        pass

                _stream_task = asyncio.create_task(_run_stream())
                await _stream_task

    except WebSocketDisconnect:
        if _stream_task and not _stream_task.done():
            _stream_task.cancel()
