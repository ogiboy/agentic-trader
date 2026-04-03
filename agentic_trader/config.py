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
