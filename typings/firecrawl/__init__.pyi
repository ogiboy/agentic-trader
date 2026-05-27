from typing import Any

class Firecrawl:
    def __init__(
        self,
        *,
        api_key: str | None = ...,
        timeout: float | int | None = ...,
        **kwargs: Any,
    ) -> None: ...
    def search(
        self,
        query: str,
        *,
        sources: list[str] | None = ...,
        limit: int | None = ...,
        timeout: int | None = ...,
        **kwargs: Any,
    ) -> object: ...
