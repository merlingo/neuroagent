from typing import Protocol


class Tool(Protocol):
    tool_id: str

    def run(self, payload: dict) -> dict:
        ...
