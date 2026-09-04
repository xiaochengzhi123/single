from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    vision_model: str = Field(
        "qwen3.7-plus", validation_alias=AliasChoices("QWEN_MODEL_VISION", "vision_model")
    )
    chat_model: str = Field(
        "qwen3.7-plus", validation_alias=AliasChoices("QWEN_MODEL_CHAT", "chat_model")
    )
    classifier_model: str = Field(
        "qwen3.7-flash",
        validation_alias=AliasChoices("QWEN_MODEL_CLASSIFIER", "classifier_model"),
    )
    tutor_model: str = Field(
        "qwen3.7-plus", validation_alias=AliasChoices("QWEN_MODEL_TUTOR", "tutor_model")
    )
    solver_model: str = Field(
        "qwen3.7-plus", validation_alias=AliasChoices("QWEN_MODEL_SOLVER", "solver_model")
    )
    verifier_model: str = Field(
        "qwen3.7-plus", validation_alias=AliasChoices("QWEN_MODEL_VERIFIER", "verifier_model")
    )
    hard_fallback_model: str = Field(
        "qwen3.8-max",
        validation_alias=AliasChoices("QWEN_MODEL_HARD_FALLBACK", "hard_fallback_model"),
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    env: str = "development"
    dashscope_api_key: str | None = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    database_url: str = "sqlite+aiosqlite:///.var/signaltutor.db"
    redis_url: str | None = None
    upload_dir: Path = Path(".var/uploads")
    learning_store_path: Path = Path(".var/learning.json")
    account_store_path: Path = Path(".var/accounts.json")
    knowledge_store_path: Path = Path(".var/knowledge.json")
    auth_secret: str = "development-only-auth-secret-change-before-deploy"
    admin_api_key: str = "development-admin-key"
    access_token_ttl_seconds: int = 7 * 24 * 60 * 60
    max_image_bytes: int = 10 * 1024 * 1024
    vision_confidence_threshold: float = 0.85
    max_solver_retries: int = 1
    model_request_timeout_seconds: float = 60
    enable_hard_model_fallback: bool = True
    agents_disable_tracing: bool = True
    use_fake_models: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def models(self) -> ModelConfig:
        return ModelConfig()

    @property
    def model_enabled(self) -> bool:
        return bool(self.dashscope_api_key) and not self.use_fake_models

    @property
    def uses_insecure_auth_defaults(self) -> bool:
        return (
            self.auth_secret == "development-only-auth-secret-change-before-deploy"
            or self.admin_api_key == "development-admin-key"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
