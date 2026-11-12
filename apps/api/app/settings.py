"""Runtime settings loaded from the environment."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed configuration; secrets never carry defaults in prod."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    opinionlab_env: str = "dev"
    deployment_mode: str = "saas"
    region: str = "cn"
    database_url: str = "postgresql+asyncpg://app:CHANGE_ME@localhost:5432/opinionlab"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    jwt_secret: str = "dev-secret-change-me-please-32-bytes"
    rate_limit_global_rps: int = 100
    rate_limit_ip_rps: int = 20
    rate_limit_user_rps: int = 30
    rate_limit_org_rps: int = 200
    connector_allowed_hosts: str = ""
    demo_max_nodes: int = 400
    demo_max_steps: int = 200
    demo_max_repeats: int = 20
    ollama_enabled: bool = False
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: float = 45.0
    use_case_review_enabled: bool = True


settings = Settings()
