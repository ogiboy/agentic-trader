from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENTIC_TRADER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    model_name: str = "qwen3:8b"
    base_url: str = "http://localhost:11434/v1"
    temperature: float = 0.0
    max_retries: int = 2
    request_timeout_seconds: float = 180.0
    max_output_tokens: int = 256

    runtime_dir: Path = Field(default_factory=lambda: Path("runtime"))
    database_path: Path = Field(default_factory=lambda: Path("runtime") / "agentic_trader.duckdb")

    strict_llm: bool = True
    allow_short: bool = True
    default_poll_seconds: int = 300
    min_confidence: float = 0.6
    max_position_pct: float = 0.1
    min_risk_reward: float = 1.5
    default_cash: float = 100_000.0

    def ensure_directories(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
