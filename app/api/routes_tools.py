from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import get_tool_registry

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolTestRequest(BaseModel):
    input_payload: dict[str, Any] = Field(default_factory=dict)


@router.get("")
def list_tools() -> list[dict]:
    return [tool.model_dump() for tool in get_tool_registry().list()]


@router.get("/{tool_id}")
def get_tool(tool_id: str) -> dict:
    try:
        return get_tool_registry().get(tool_id).model_dump()
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{tool_id}/test")
def test_tool(tool_id: str, request: ToolTestRequest) -> dict:
    try:
        return get_tool_registry().run(tool_id, request.input_payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
