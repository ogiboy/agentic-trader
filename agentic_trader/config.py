from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from agentic_trader.schemas import RuntimeMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENTIC_TRADER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: Literal["ollama"] = "ollama"
    model_name: str = "qwen3:8b"
    coordinator_model_name: str | None = None
    regime_model_name: str | None = None
    strategy_model_name: str | None = None
    risk_model_name: str | None = None
    manager_model_name: str | None = None
    explainer_model_name: str | None = None
    instruction_model_name: str | None = None
    base_url: str = "http://localhost:11434/v1"
    temperature: float = 0.0
    max_retries: int = 2
    request_timeout_seconds: float = 180.0
    max_output_tokens: int = 8192

    runtime_dir: Path = Field(default_factory=lambda: Path("runtime"))
    database_path: Path = Field(
        default_factory=lambda: Path("runtime") / "agentic_trader.duckdb"
    )
    market_data_cache_dir: Path = Field(
        default_factory=lambda: Path("runtime") / "market_snapshots"
    )
    market_data_mode: Literal["live", "prefer_cache", "refresh_cache"] = "live"
    news_mode: Literal["off", "yfinance"] = "off"
    news_headline_limit: int = 5

    runtime_mode: RuntimeMode = "operation"
    strict_llm: bool = True
    execution_backend: Literal["paper", "live"] = "paper"
    live_execution_enabled: bool = False
    execution_kill_switch_active: bool = False
    allow_short: bool = True
    default_poll_seconds: int = 300
    min_confidence: float = 0.6
    max_position_pct: float = 0.1
    max_gross_exposure_pct: float = 0.8
    max_open_positions: int = 5
    min_risk_reward: float = 1.5
    default_cash: float = 100_000.0

    def ensure_directories(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.market_data_cache_dir.mkdir(parents=True, exist_ok=True)

    def model_for_role(self, role: str) -> str:
        mapping = {
            "coordinator": self.coordinator_model_name,
            "regime": self.regime_model_name,
            "strategy": self.strategy_model_name,
            "risk": self.risk_model_name,
            "manager": self.manager_model_name,
            "explainer": self.explainer_model_name,
            "instruction": self.instruction_model_name,
        }
        return mapping.get(role) or self.model_name

    def model_routing(self) -> dict[str, str]:
        return {
            "default": self.model_name,
            "coordinator": self.model_for_role("coordinator"),
            "regime": self.model_for_role("regime"),
            "strategy": self.model_for_role("strategy"),
            "risk": self.model_for_role("risk"),
            "manager": self.model_for_role("manager"),
            "explainer": self.model_for_role("explainer"),
            "instruction": self.model_for_role("instruction"),
        }


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
