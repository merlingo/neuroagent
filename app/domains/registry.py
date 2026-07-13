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

        Missing required fields are filled with sensible defaults derived from
        directory/file names so that externally-written YAMLs (e.g. from
        Intravision's ContractsWriterService) work without strict adherence
        to the full contract schema.
        """
        domain_id = domain_dir.name
        manifest = domain_dir / "domain.yaml"
        if manifest.exists():
            raw = yaml.safe_load(manifest.read_text()) or {}
        else:
            # No domain.yaml — synthesize a minimal domain from directory name
            raw = {}
        # Fill defaults for required DomainContract fields
        raw.setdefault("domain_id", domain_id)
        raw.setdefault("name", domain_id)
        raw.setdefault("version", "1.0.0")
        domain = DomainContract.model_validate(raw)
        self.domains[domain.domain_id] = domain

        # Collect agent YAML files
        agent_files: list[Path] = []
        agents_dir = domain_dir / "agents"
        if agents_dir.is_dir():
            agent_files = sorted(agents_dir.glob("*.yaml"))
        else:
            agent_files = sorted(
                f for f in domain_dir.glob("*.yaml") if f.name != "domain.yaml"
            )

        for agent_file in agent_files:
            try:
                raw_agent = yaml.safe_load(agent_file.read_text()) or {}
            except Exception:
                continue  # Skip unparseable YAML files
            if not isinstance(raw_agent, dict):
                continue
            # Fill defaults for required AgentContract fields
            file_stem = agent_file.stem
            raw_agent.setdefault("agent_id", f"{domain_id}.{file_stem}")
            raw_agent.setdefault("name", raw_agent["agent_id"])
            raw_agent["version"] = str(raw_agent.get("version", "1.0.0"))  # coerce int→str
            raw_agent.setdefault("domain", domain_id)
            raw_agent.setdefault("role", raw_agent.get("description", "agent"))
            raw_agent.setdefault("goal", raw_agent.get("description", "execute tasks"))
            raw_agent.setdefault("input_schema", {"type": "object", "properties": {}, "required": []})
            raw_agent.setdefault("output_schema", {"type": "object", "properties": {}, "required": []})
            agent = AgentContract.model_validate(raw_agent)
            self.agents[agent.agent_id] = agent

        return domain
