from pathlib import Path

from app.domains.registry import DomainRegistry
from app.db.repositories import get_repository
from app.settings import Settings, get_settings
from app.tools.registry import ToolRegistry

# Module-level singleton — initialised from CONTRACTS_DIR on first access.
# reload_domain updates it in-place via load_domain_from_directory().
_domain_registry: DomainRegistry | None = None


def get_domain_registry() -> DomainRegistry:
    global _domain_registry
    if _domain_registry is None:
        settings = get_settings()
        contracts_path = Path(settings.contracts_dir)
        if contracts_path.is_dir():
            _domain_registry = DomainRegistry.from_directory(contracts_path)
        else:
            _domain_registry = DomainRegistry(domains={}, agents={})
    return _domain_registry


def get_tool_registry() -> ToolRegistry:
    return ToolRegistry.from_default_path()


def get_app_settings() -> Settings:
    return get_settings()


def get_repository_dependency():
    return get_repository()
