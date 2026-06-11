from app.contracts.agent_contract import AgentContract
from app.contracts.workflow_contract import ExecutionPlan, WorkflowStep


class SimplePlanner:
    def create_plan(self, agent: AgentContract) -> ExecutionPlan:
        steps: list[WorkflowStep] = [
            WorkflowStep(step_id="understand_request", type="agent_reasoning"),
            WorkflowStep(
                step_id="produce_output",
                type="agent_reasoning",
                depends_on=["understand_request"],
            ),
        ]
        if "obsidian.write_note" in agent.allowed_tools:
            steps.append(
                WorkflowStep(
                    step_id="write_obsidian_note",
                    type="tool_call",
                    tool="obsidian.write_note",
                    approval_required=False,
                    depends_on=["produce_output"],
                )
            )
        return ExecutionPlan(
            intent="agent_run",
            domain=agent.domain,
            agent_id=agent.agent_id,
            steps=steps,
            approval_points=agent.human_approval_required_for,
            expected_artifacts=["run_trace.json", "final_output.json"],
        )
