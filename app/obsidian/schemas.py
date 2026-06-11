from pydantic import BaseModel


class ObsidianNote(BaseModel):
    path: str
    content: str
