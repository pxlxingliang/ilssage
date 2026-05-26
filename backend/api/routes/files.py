import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/api/v1/files")
async def serve_file(path: str = Query(..., description="Absolute path to the file")):
    file_path = Path(path).resolve()

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    media_type, _ = mimetypes.guess_type(str(file_path))
    if not media_type:
        media_type = "application/octet-stream"

    return FileResponse(file_path, media_type=media_type)
