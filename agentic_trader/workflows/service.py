import time
from dataclasses import dataclass

from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import LLMHealthStatus, RunArtifacts
from agentic_trader.workflows.run_once import persist_run, run_once


@dataclass
class ServiceCycleResult:
    symbol: str
    artifacts: RunArtifacts
    order_id: str


def ensure_llm_ready(settings: Settings) -> LLMHealthStatus:
    health = LocalLLM(settings).health_check()
    if not health.service_reachable:
        raise RuntimeError(health.message)
    if settings.strict_llm and not health.model_available:
        raise RuntimeError(health.message)
    return health


def run_service(
    *,
    settings: Settings,
    symbols: list[str],
    interval: str,
    lookback: str,
    poll_seconds: int,
    continuous: bool,
    max_cycles: int | None,
) -> list[ServiceCycleResult]:
    ensure_llm_ready(settings)

    cycle_results: list[ServiceCycleResult] = []
    cycle_count = 0
    while True:
        cycle_count += 1
        for symbol in symbols:
            artifacts = run_once(
                settings=settings,
                symbol=symbol,
                interval=interval,
                lookback=lookback,
                allow_fallback=False,
            )
            order_id = persist_run(settings=settings, artifacts=artifacts)
            cycle_results.append(
                ServiceCycleResult(
                    symbol=symbol,
                    artifacts=artifacts,
                    order_id=order_id,
                )
            )

        if not continuous:
            break
        if max_cycles is not None and cycle_count >= max_cycles:
            break
        time.sleep(poll_seconds)

    return cycle_results
