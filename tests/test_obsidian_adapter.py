from app.obsidian.note_writer import ObsidianNoteWriter
from app.obsidian.note_reader import ObsidianNoteReader
from app.settings import Settings


def test_obsidian_note_writer_returns_frontmatter() -> None:
    note = ObsidianNoteWriter().write_note("Demo", "Body")
    assert note["path"] == "00_Inbox/Demo.md"
    assert note["content"].startswith("---")


def test_obsidian_note_writer_writes_to_configured_vault_when_enabled(tmp_path) -> None:
    settings = Settings(obsidian_enabled=True, obsidian_vault_path=str(tmp_path))
    note = ObsidianNoteWriter(settings).write_note("Demo/Run", "Body", "03_Agent_Runs/Daily")

    assert note["status"] == "written"
    assert note["path"] == "03_Agent_Runs/Daily/Demo-Run.md"
    assert (tmp_path / note["path"]).read_text(encoding="utf-8").startswith("---")


def test_obsidian_note_reader_searches_configured_vault_when_enabled(tmp_path) -> None:
    settings = Settings(obsidian_enabled=True, obsidian_vault_path=str(tmp_path))
    ObsidianNoteWriter(settings).write_note("Research", "NeuroAgent memory note", "01_Research")

    results = ObsidianNoteReader(settings).search("memory")

    assert results[0]["path"] == "01_Research/Research.md"
    assert results[0]["status"] == "found"
