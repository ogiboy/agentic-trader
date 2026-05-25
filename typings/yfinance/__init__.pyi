from typing import Any

import pandas as pd

def download(
    tickers: str,
    *,
    period: str,
    interval: str,
    auto_adjust: bool = ...,
    progress: bool = ...,
    **kwargs: Any,
) -> pd.DataFrame: ...

class Ticker:
    def __init__(self, ticker: str, **kwargs: Any) -> None: ...
    @property
    def news(self) -> list[dict[str, Any]]: ...
