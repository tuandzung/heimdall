from __future__ import annotations

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(override=False)


class K8sOperatorSettings(BaseSettings):
    enabled: bool = True
    namespace_to_watch: str = "default"
    label_selector: str | None = None

    model_config = SettingsConfigDict(env_prefix="HEIMDALL_JOBLOCATOR_K8S_OPERATOR_", env_nested_delimiter="__")


class JobLocatorSettings(BaseSettings):
    k8s_operator: K8sOperatorSettings = K8sOperatorSettings()

    model_config = SettingsConfigDict(env_prefix="HEIMDALL_JOBLOCATOR_", env_nested_delimiter="__")


class AuthSettings(BaseSettings):
    enabled: bool = False
    google_client_id: str | None = None
    google_client_secret: str | None = None
    redirect_url: str | None = None
    allowed_emails: list[str] = []
    allowed_domains: list[str] = []
    session_secret_key: str = "change-me"
    database_url: str = "sqlite+aiosqlite:///./heimdall.db"
    cookie_name: str = "heimdall_auth"
    cookie_max_age: int = 3600
    cookie_path: str = "/"
    cookie_secure: bool = False
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"

    model_config = SettingsConfigDict(env_prefix="HEIMDALL_AUTH_", env_nested_delimiter="__")


class AppConfig(BaseSettings):
    joblocator: JobLocatorSettings = JobLocatorSettings()
    auth: AuthSettings = AuthSettings()
    patterns: dict[str, str] = {}
    endpoint_path_patterns: dict[str, str] = {}
    debug: bool = False
    jobs_cache_ttl: int = 10
    allowed_origins: list[str] = ["*"]
    # Optional mapping of app name -> base URL, e.g., {"orders": "http://orders-ui:8081"}
    proxy_target_map: dict[str, str] = {}

    # Also expose an app version (can be set via env or falls back to package)
    app_version: str | None = None

    model_config = SettingsConfigDict(env_prefix="HEIMDALL_", env_nested_delimiter="__")

    def resolved_app_version(self, fallback_version: str) -> str:
        return self.app_version or fallback_version
