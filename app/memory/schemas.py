from pydantic import BaseModel


class MemoryRecord(BaseModel):
    scope: str
    key: str
    value: str
