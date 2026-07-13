from functools import lru_cache
import os

from pydantic import BaseModel, Field


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    app_name: str = "neuroagent-framework"
    app_env: str = "development"
    app_debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str | None = None
    repository_backend: str = "memory"
    redis_url: str = "redis://localhost:6379/0"
    vector_backend: str = "qdrant"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_prefix: str = "neuroagent"
    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = ""
    artifact_inline_max_bytes: int = 65536
    default_tenant_id: str = "default"
    api_auth_enabled: bool = False
    api_keys: str = ""
    admin_api_keys: str = ""
    model_provider: str = "stub"
    default_model: str = "gpt-4.1-mini"
    default_embedding_model: str = "text-embedding-3-small"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4.1-mini"
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_model: str = "gemini-2.5-flash"
    ollama_base_url: str = "http://ollama:11434/v1"
    ollama_model: str = "deepseek-r1"
    ollama_deepseek_r1_model: str = "deepseek-r1"
    ollama_kimi_k26_model: str = "kimi-k2.6"
    ollama_glm_51_model: str = "glm-5.1"
    ollama_qwen_35_model: str = "qwen3.5"
    ollama_qwen25_coder_model: str = "qwen2.5-coder"
    ollama_gemma4_model: str = "gemma4"
    model_timeout_seconds: int = 60
    model_temperature: float = 0.2
    model_max_tokens: int = 1200
    obsidian_enabled: bool = False
    obsidian_base_url: str = "http://127.0.0.1:27123"
    obsidian_api_key: str = ""
    obsidian_vault_name: str = "NeuroAgentVault"
    obsidian_web_url: str = "http://127.0.0.1:3000"
    obsidian_vault_path: str = "app/obsidian/vaults/NeuroAgentVault"
    enable_mcp: bool = False
    file_tool_root: str = "."
    github_token: str = ""
    github_api_base_url: str = "https://api.github.com"
    github_default_owner: str = ""
    github_default_repo: str = ""
    github_timeout_seconds: int = 20
    log_level: str = "INFO"
    enable_tracing: bool = True
    project_root: str = Field(default=".")
    contracts_dir: str = "app/domains"
    neuroagent_allowed_models: str = ""
    neuroagent_loop_context_max_chars: int = 24000
    neuroagent_critic_model: str = "gpt-4.1-mini"
    neuroagent_default_max_steps: int = 20
    neuroagent_default_max_tokens: int = 100000


@lru_cache
def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL")
    repository_backend = os.getenv("REPOSITORY_BACKEND")
    if repository_backend is None:
        repository_backend = "postgres" if database_url else "memory"
    return Settings(
        app_name=os.getenv("APP_NAME", "neuroagent-framework"),
        app_env=os.getenv("APP_ENV", "development"),
        app_debug=_env_bool("APP_DEBUG", True),
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("API_PORT", "8000")),
        database_url=database_url,
        repository_backend=repository_backend,
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        vector_backend=os.getenv("VECTOR_BACKEND", "qdrant"),
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY", ""),
        qdrant_collection_prefix=os.getenv("QDRANT_COLLECTION_PREFIX", "neuroagent"),
        s3_endpoint=os.getenv("S3_ENDPOINT", ""),
        s3_access_key=os.getenv("S3_ACCESS_KEY", ""),
        s3_secret_key=os.getenv("S3_SECRET_KEY", ""),
        s3_bucket=os.getenv("S3_BUCKET", ""),
        artifact_inline_max_bytes=int(os.getenv("ARTIFACT_INLINE_MAX_BYTES", "65536")),
        default_tenant_id=os.getenv("DEFAULT_TENANT_ID", "default"),
        api_auth_enabled=_env_bool("API_AUTH_ENABLED", False),
        api_keys=os.getenv("API_KEYS", ""),
        admin_api_keys=os.getenv("ADMIN_API_KEYS", ""),
        model_provider=os.getenv("MODEL_PROVIDER", "stub"),
        default_model=os.getenv("DEFAULT_MODEL", "gpt-4.1-mini"),
        default_embedding_model=os.getenv("DEFAULT_EMBEDDING_MODEL", "text-embedding-3-small"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", os.getenv("CLAUDE_API_KEY", "")),
        anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_base_url=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1"),
        ollama_model=os.getenv("OLLAMA_MODEL", "deepseek-r1"),
        ollama_deepseek_r1_model=os.getenv("OLLAMA_DEEPSEEK_R1_MODEL", "deepseek-r1"),
        ollama_kimi_k26_model=os.getenv("OLLAMA_KIMI_K26_MODEL", "kimi-k2.6"),
        ollama_glm_51_model=os.getenv("OLLAMA_GLM_51_MODEL", "glm-5.1"),
        ollama_qwen_35_model=os.getenv("OLLAMA_QWEN_35_MODEL", "qwen3.5"),
        ollama_qwen25_coder_model=os.getenv("OLLAMA_QWEN25_CODER_MODEL", "qwen2.5-coder"),
        ollama_gemma4_model=os.getenv("OLLAMA_GEMMA4_MODEL", "gemma4"),
        model_timeout_seconds=int(os.getenv("MODEL_TIMEOUT_SECONDS", "60")),
        model_temperature=float(os.getenv("MODEL_TEMPERATURE", "0.2")),
        model_max_tokens=int(os.getenv("MODEL_MAX_TOKENS", "1200")),
        obsidian_enabled=_env_bool("OBSIDIAN_ENABLED", False),
        obsidian_base_url=os.getenv("OBSIDIAN_BASE_URL", "http://127.0.0.1:27123"),
        obsidian_api_key=os.getenv("OBSIDIAN_API_KEY", ""),
        obsidian_vault_name=os.getenv("OBSIDIAN_VAULT_NAME", "NeuroAgentVault"),
        obsidian_web_url=os.getenv("OBSIDIAN_WEB_URL", "http://127.0.0.1:3000"),
        obsidian_vault_path=os.getenv("OBSIDIAN_VAULT_PATH", "app/obsidian/vaults/NeuroAgentVault"),
        enable_mcp=_env_bool("ENABLE_MCP", False),
        file_tool_root=os.getenv("FILE_TOOL_ROOT", os.getenv("PROJECT_ROOT", ".")),
        github_token=os.getenv("GITHUB_TOKEN", ""),
        github_api_base_url=os.getenv("GITHUB_API_BASE_URL", "https://api.github.com"),
        github_default_owner=os.getenv("GITHUB_DEFAULT_OWNER", ""),
        github_default_repo=os.getenv("GITHUB_DEFAULT_REPO", ""),
        github_timeout_seconds=int(os.getenv("GITHUB_TIMEOUT_SECONDS", "20")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        enable_tracing=_env_bool("ENABLE_TRACING", True),
        contracts_dir=os.getenv("CONTRACTS_DIR", "app/domains"),
        neuroagent_allowed_models=os.getenv("NEUROAGENT_ALLOWED_MODELS", ""),
        neuroagent_loop_context_max_chars=int(os.getenv("NEUROAGENT_LOOP_CONTEXT_MAX_CHARS", "24000")),
        neuroagent_critic_model=os.getenv("NEUROAGENT_CRITIC_MODEL", "gpt-4.1-mini"),
        neuroagent_default_max_steps=int(os.getenv("NEUROAGENT_DEFAULT_MAX_STEPS", "20")),
        neuroagent_default_max_tokens=int(os.getenv("NEUROAGENT_DEFAULT_MAX_TOKENS", "100000")),
    )
