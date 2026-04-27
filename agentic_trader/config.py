from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from agentic_trader.schemas import ExecutionBackend, RuntimeMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENTIC_TRADER_",
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    llm_provider: Literal["ollama"] = "ollama"
    model_name: str = Field(
        default="qwen3:8b",
        validation_alias=AliasChoices(
            "AGENTIC_TRADER_MODEL_NAME",
            "AGENTIC_TRADER_MODEL",
        ),
    )
    coordinator_model_name: str | None = None
    regime_model_name: str | None = None
    strategy_model_name: str | None = None
    risk_model_name: str | None = None
    manager_model_name: str | None = None
    fundamental_model_name: str | None = None
    macro_model_name: str | None = None
    explainer_model_name: str | None = None
    instruction_model_name: str | None = None
    base_url: str = "http://localhost:11434/v1"
    temperature: float = 0.0
    max_retries: int = 2
    request_timeout_seconds: float = 180.0
    max_output_tokens: int = 2048

    runtime_dir: Path = Field(default_factory=lambda: Path("runtime"))
    database_path: Path = Field(
        default_factory=lambda: Path("runtime") / "agentic_trader.duckdb"
    )
    market_data_cache_dir: Path = Field(
        default_factory=lambda: Path("runtime") / "market_snapshots"
    )
    finnhub_api_key: str | None = None
    fmp_api_key: str | None = None
    polygon_api_key: str | None = None
    massive_api_key: str | None = None
    alpaca_api_key: str | None = None
    alpaca_secret_key: str | None = None
    alpaca_base_url: str = "https://paper-api.alpaca.markets/v2"
    alpaca_data_feed: str = "iex"
    market_data_mode: Literal["live", "prefer_cache", "refresh_cache"] = "live"
    news_mode: Literal["off", "yfinance"] = "off"
    news_headline_limit: int = 5

    runtime_mode: RuntimeMode = "operation"
    strict_llm: bool = True
    execution_backend: ExecutionBackend = "paper"
    live_execution_enabled: bool = False
    execution_kill_switch_active: bool = False
    simulated_slippage_bps: float = Field(default=5.0, ge=0.0)
    simulated_spread_bps: float = Field(default=2.0, ge=0.0)
    simulated_price_drift_bps: float = Field(default=3.0, ge=0.0)
    simulated_partial_fill_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    simulated_partial_fill_min_ratio: float = Field(default=0.5, gt=0.0, le=1.0)
    simulated_order_rejection_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    simulated_latency_ms: int = Field(default=0, ge=0)
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
            "fundamental": self.fundamental_model_name,
            "macro": self.macro_model_name,
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
            "fundamental": self.model_for_role("fundamental"),
            "macro": self.model_for_role("macro"),
            "explainer": self.model_for_role("explainer"),
            "instruction": self.model_for_role("instruction"),
        }


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
