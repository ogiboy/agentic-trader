from agentic_trader.config import Settings
from agentic_trader.features.fundamental import get_fundamental_features
from agentic_trader.features.macro import get_macro_context
from agentic_trader.features.symbols import resolve_symbol_identity
from agentic_trader.features.technical import get_market_features
from agentic_trader.schemas import (
    CanonicalAnalysisSnapshot,
    DecisionFeatureBundle,
    InvestmentPreferences,
    MarketSnapshot,
    NewsSignal,
)


def build_decision_feature_bundle(
    snapshot: MarketSnapshot,
    *,
    settings: Settings,
    preferences: InvestmentPreferences | None = None,
    news_items: list[NewsSignal] | None = None,
    canonical_snapshot: CanonicalAnalysisSnapshot | None = None,
) -> DecisionFeatureBundle:
    """Build the structured decision feature bundle consumed by specialist agents."""
    symbol_identity = (
        canonical_snapshot.symbol_identity
        if canonical_snapshot is not None
        else resolve_symbol_identity(snapshot.symbol, preferences)
    )
    return DecisionFeatureBundle(
        symbol_identity=symbol_identity,
        technical=get_market_features(snapshot),
        fundamental=get_fundamental_features(
            symbol_identity,
            settings=settings,
            fundamental_snapshot=(
                canonical_snapshot.fundamental
                if canonical_snapshot is not None
                else None
            ),
        ),
        macro=get_macro_context(
            symbol_identity,
            settings=settings,
            news_items=news_items,
            news_events=(
                canonical_snapshot.news_events
                if canonical_snapshot is not None
                else None
            ),
            macro_snapshot=(
                canonical_snapshot.macro if canonical_snapshot is not None else None
            ),
        ),
    )
