from fastapi import APIRouter, HTTPException

from backend.deps import get_llm_service, get_session_service
from backend.services.title_service import generate_title

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("")
async def list_sessions():
    sess = get_session_service()
    return {"sessions": sess.list_sessions()}


@router.post("")
async def create_session():
    llm = get_llm_service()
    sess = get_session_service()
    current = llm.get_current_model()
    session = sess.create_session(
        model_provider=current.get("provider", ""),
        model_name=current.get("id", ""),
    )
    return session


@router.get("/{session_id}")
async def get_session(session_id: str):
    sess = get_session_service()
    session = sess.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/{session_id}")
async def update_session(session_id: str, data: dict):
    sess = get_session_service()
    updated = sess.update_session(session_id, **data)
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found")
    return updated


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    sess = get_session_service()
    if not sess.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}


@router.post("/{session_id}/generate-title")
async def generate_session_title(session_id: str):
    sess = get_session_service()
    llm = get_llm_service()
    session = sess.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = sess.get_messages(session_id, limit=100)
    user_contents = []
    for msg in messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if content and content.strip():
                user_contents.append(content.strip()[:200])
        if len(user_contents) >= 10:
            break

    if not user_contents:
        raise HTTPException(status_code=400, detail="No user message found in session")

    combined = "\n\n".join(
        c[:300] for c in user_contents
    )

    title = await generate_title(combined, llm)
    if not title:
        raise HTTPException(
            status_code=500,
            detail="Title generation returned no result. The LLM may be unavailable or the response was invalid.",
        )

    sess.update_session(session_id, title=title)
    return {"title": title}
