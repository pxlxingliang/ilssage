from fastapi import APIRouter

from backend.deps import get_llm_service

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])


@router.get("/models")
async def list_models():
    llm = get_llm_service()
    return {"models": llm.list_models()}


@router.get("/current")
async def get_current():
    llm = get_llm_service()
    return llm.get_current_model()


@router.post("/switch")
async def switch_model(data: dict):
    llm = get_llm_service()
    model_id = data.get("model_id", "")
    if not model_id:
        return {"error": "model_id required"}
    llm.switch_model(model_id)
    return llm.get_current_model()
