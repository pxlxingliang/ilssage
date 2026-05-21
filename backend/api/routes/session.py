from fastapi import APIRouter, HTTPException

from backend.deps import get_session_service, get_llm_service

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
