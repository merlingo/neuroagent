from datetime import UTC, datetime
from pathlib import Path

from app.settings import Settings, get_settings


class ObsidianNoteWriter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def write_note(self, title: str, body: str, folder: str = "00_Inbox") -> dict:
        safe_title = _safe_segment(title, default="Untitled")
        safe_folder = _safe_folder(folder)
        frontmatter = (
            "---\n"
            "type: neuroagent_note\n"
            f"created_at: {datetime.now(UTC).isoformat()}\n"
            "tags:\n"
            "  - neuroagent\n"
            "---\n\n"
        )
        path = f"{safe_folder}/{safe_title}.md"
        content = frontmatter + body
        if self.settings.obsidian_enabled:
            vault_path = Path(self.settings.obsidian_vault_path).expanduser().resolve()
            note_path = (vault_path / path).resolve()
            if vault_path not in note_path.parents:
                raise ValueError("Obsidian note path escapes configured vault")
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(content, encoding="utf-8")
            status = "written"
        else:
            status = "stubbed"
        return {
            "path": path,
            "content": content,
            "status": status,
        }


def _safe_folder(folder: str) -> str:
    parts = [_safe_segment(part, default="") for part in folder.split("/")]
    safe = [part for part in parts if part and part not in {".", ".."}]
    return "/".join(safe) or "00_Inbox"


def _safe_segment(value: str, default: str) -> str:
    safe = value.replace("\\", "-").replace("/", "-").strip()
    safe = "".join(char for char in safe if char.isalnum() or char in {" ", "-", "_", "."}).strip()
    return safe or default
