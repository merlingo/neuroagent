from app.core.runtime import AgentRuntime


class Orchestrator:
    def __init__(self, runtime: AgentRuntime) -> None:
        self.runtime = runtime
