from pathlib import Path

import yaml

from app.contracts.agent_contract import AgentContract
from app.contracts.domain_contract import DomainContract
from app.core.errors import ContractNotFoundError


class DomainRegistry:
    def __init__(self, domains: dict[str, DomainContract], agents: dict[str, AgentContract]) -> None:
        self.domains = domains
        self.agents = agents

    @classmethod
    def from_default_path(cls) -> "DomainRegistry":
        return cls.from_directory(Path("app/domains"))

    @classmethod
    def from_directory(cls, root: Path) -> "DomainRegistry":
        domains: dict[str, DomainContract] = {}
        agents: dict[str, AgentContract] = {}
        for domain_file in sorted(root.glob("*/domain.yaml")):
            domain = DomainContract.model_validate(yaml.safe_load(domain_file.read_text()))
            domains[domain.domain_id] = domain
            for agent_file in sorted((domain_file.parent / "agents").glob("*.yaml")):
                agent = AgentContract.model_validate(yaml.safe_load(agent_file.read_text()))
                agents[agent.agent_id] = agent
        return cls(domains, agents)

    def list_domains(self) -> list[DomainContract]:
        return sorted(self.domains.values(), key=lambda item: item.domain_id)

    def get_domain(self, domain_id: str) -> DomainContract:
        try:
            return self.domains[domain_id]
        except KeyError as exc:
            raise ContractNotFoundError(f"Domain {domain_id} not found") from exc

    def list_agents(self) -> list[AgentContract]:
        return sorted(self.agents.values(), key=lambda item: item.agent_id)

    def get_agent(self, agent_id: str) -> AgentContract:
        try:
            return self.agents[agent_id]
        except KeyError as exc:
            raise ContractNotFoundError(f"Agent {agent_id} not found") from exc

    def load_domain_from_directory(self, domain_dir: Path) -> DomainContract:
        """Load (or reload) a single domain and its agents from a directory.

        The directory must contain a domain.yaml file. Agent YAMLs are loaded
        from an 'agents/' subdirectory if present, or from *.yaml files in the
        domain directory itself (excluding domain.yaml).
        """
        manifest = domain_dir / "domain.yaml"
        if not manifest.exists():
            raise ContractNotFoundError(
                f"Domain manifest not found at {manifest}"
            )
        domain = DomainContract.model_validate(yaml.safe_load(manifest.read_text()))
        self.domains[domain.domain_id] = domain

        # Load agents from agents/ subdirectory (standard layout)
        agents_dir = domain_dir / "agents"
        if agents_dir.is_dir():
            for agent_file in sorted(agents_dir.glob("*.yaml")):
                agent = AgentContract.model_validate(yaml.safe_load(agent_file.read_text()))
                self.agents[agent.agent_id] = agent
        else:
            # Fallback: load *.yaml files in domain dir (excluding domain.yaml)
            for agent_file in sorted(domain_dir.glob("*.yaml")):
                if agent_file.name == "domain.yaml":
                    continue
                agent = AgentContract.model_validate(yaml.safe_load(agent_file.read_text()))
                self.agents[agent.agent_id] = agent

        return domain
