from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.contracts.agent_contract import AgentContract
from app.domains.registry import DomainRegistry


def test_domain_registry_loads_seed_contracts() -> None:
    registry = DomainRegistry.from_default_path()
    assert "research" in registry.domains
    assert "cybersecurity.sigma_rule_agent" in registry.agents


def test_invalid_agent_contract_fails(tmp_path: Path) -> None:
    invalid = {"agent_id": "bad"}
    with pytest.raises(ValidationError):
        AgentContract.model_validate(invalid)


def test_agent_yaml_contract_validates() -> None:
    raw = yaml.safe_load(Path("app/domains/research/agents/literature_researcher.yaml").read_text())
    agent = AgentContract.model_validate(raw)
    assert agent.agent_id == "research.literature_researcher"
