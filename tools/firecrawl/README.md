# Firecrawl Tool Root

This directory is reserved for Firecrawl adapter metadata and local integration
notes. Firecrawl remains optional and user-authenticated through
`FIRECRAWL_API_KEY` for the Python SDK path or `firecrawl login --browser` for
the CLI fallback.

Do not store API keys, raw scraped pages, or prompt-ready article text here.
Research providers must normalize evidence with source attribution, freshness,
materiality, and redaction before the core runtime sees it.
