from pathlib import Path

from app.domains.registry import DomainRegistry
from app.db.repositories import get_repository
from app.settings import Settings, get_settings
from app.tools.registry import ToolRegistry

# Built-in domain definitions shipped with the image.
_BUILTIN_DOMAINS = Path("app/domains")

# Module-level singleton. Populated at startup via lifespan hook.
# reload_domain() updates it in-place via load_domain_from_directory().
_domain_registry: DomainRegistry | None = None


def _build_registry() -> DomainRegistry:
    """Load built-in domains first, then overlay user contracts from CONTRACTS_DIR."""
    settings = get_settings()
    contracts_dir = Path(settings.contracts_dir)

    # Start from built-in domains baked into the image
    if _BUILTIN_DOMAINS.is_dir():
        registry = DomainRegistry.from_directory(_BUILTIN_DOMAINS)
    else:
        registry = DomainRegistry(domains={}, agents={})

    # Overlay user-written contracts from the external volume (CONTRACTS_DIR)
    if contracts_dir.is_dir() and contracts_dir.resolve() != _BUILTIN_DOMAINS.resolve():
        for sub in sorted(contracts_dir.iterdir()):
            if sub.is_dir():
                try:
                    registry.load_domain_from_directory(sub)
                except Exception:
                    pass

    return registry


def get_domain_registry() -> DomainRegistry:
    global _domain_registry
    if _domain_registry is None:
        _domain_registry = _build_registry()
    return _domain_registry


def get_tool_registry() -> ToolRegistry:
    return ToolRegistry.from_default_path()


def get_app_settings() -> Settings:
    return get_settings()


def get_repository_dependency():
    return get_repository()
