from fastapi import APIRouter

from app.model_gateway import model_status

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/status")
def get_model_status() -> dict:
    return model_status()
