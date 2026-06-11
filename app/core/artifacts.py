from app.contracts.artifact_contract import ArtifactContract


class ArtifactWriter:
    def build_run_trace(self, run: dict) -> ArtifactContract:
        return ArtifactContract(
            artifact_type="json",
            name="run_trace.json",
            content=run,
            metadata={"run_id": run["id"]},
        )
