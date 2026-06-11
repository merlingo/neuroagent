from pathlib import Path

from app.settings import Settings, get_settings


class ObsidianNoteReader:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def search(self, query: str) -> list[dict]:
        if self.settings.obsidian_enabled:
            return self._search_vault(query)
        return [{"query": query, "status": "stubbed"}]

    def _search_vault(self, query: str) -> list[dict]:
        vault_path = Path(self.settings.obsidian_vault_path).expanduser().resolve()
        needle = query.lower()
        results: list[dict] = []
        if not vault_path.exists():
            return results
        for path in sorted(vault_path.rglob("*.md")):
            content = path.read_text(encoding="utf-8")
            if needle not in content.lower() and needle not in path.name.lower():
                continue
            results.append(
                {
                    "path": str(path.relative_to(vault_path)),
                    "title": path.stem,
                    "snippet": _snippet(content, needle),
                    "status": "found",
                }
            )
        return results


def _snippet(content: str, needle: str) -> str:
    lowered = content.lower()
    index = lowered.find(needle)
    if index == -1:
        return content[:200]
    start = max(0, index - 80)
    end = min(len(content), index + len(needle) + 120)
    return content[start:end]
