from pydantic import BaseModel, Field


class EvalContract(BaseModel):
    eval_id: str
    name: str
    description: str = ""
    required_for_domains: list[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    eval_name: str
    passed: bool
    score: float = 1.0
    rubric: str = ""
    findings: list[str] = Field(default_factory=list)
