from fastapi import APIRouter
from pydantic import BaseModel

from app.obsidian.note_reader import ObsidianNoteReader
from app.obsidian.note_writer import ObsidianNoteWriter

router = APIRouter(prefix="/obsidian", tags=["obsidian"])
writer = ObsidianNoteWriter()
reader = ObsidianNoteReader()


class NoteRequest(BaseModel):
    title: str
    body: str
    folder: str = "00_Inbox"


@router.post("/notes")
def write_note(request: NoteRequest) -> dict:
    return writer.write_note(request.title, request.body, request.folder)


@router.get("/notes/search")
def search_notes(query: str) -> list[dict]:
    return reader.search(query)


@router.post("/agent-run-note")
def write_agent_run_note(request: NoteRequest) -> dict:
    return writer.write_note(request.title, request.body, "03_Agent_Runs/Daily")
