from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.deps import get_session_service
from backend.services.chat_service import stream_chat, run_chat

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatRequest(BaseModel):
    content: str


@router.post("/{session_id}/send")
async def send_message(session_id: str, req: ChatRequest):
    sess = get_session_service()
    if not sess.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    response = await run_chat(session_id, req.content)
    return {"content": response, "session_id": session_id}


@router.post("/{session_id}/stream")
async def stream_message(session_id: str, req: ChatRequest):
    sess = get_session_service()
    if not sess.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    async def generate():
        async for event in stream_chat(session_id, req.content):
            yield event.to_sse()
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{session_id}/history")
async def get_history(session_id: str):
    sess = get_session_service()
    if not sess.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"messages": sess.get_messages(session_id)}
