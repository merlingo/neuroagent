from app.domains.registry import DomainRegistry
from app.db.repositories import get_repository
from app.settings import Settings, get_settings
from app.tools.registry import ToolRegistry


def get_domain_registry() -> DomainRegistry:
    return DomainRegistry.from_default_path()


def get_tool_registry() -> ToolRegistry:
    return ToolRegistry.from_default_path()


def get_app_settings() -> Settings:
    return get_settings()


def get_repository_dependency():
    return get_repository()
