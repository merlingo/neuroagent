from pathlib import Path


class PromptRegistry:
    def __init__(self, root: Path = Path("app/prompts/templates")) -> None:
        self.root = root

    def load(self, name: str) -> str:
        return (self.root / name).read_text()
