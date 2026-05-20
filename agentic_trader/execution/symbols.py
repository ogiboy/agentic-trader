def is_v1_us_equity_symbol(symbol: str) -> bool:
    normalized = symbol.strip().upper()
    if not normalized or len(normalized) > 10:
        return False
    if not all(char.isalnum() or char in {".", "-"} for char in normalized):
        return False
    parts = normalized.split(".")
    if len(parts) > 2:
        return False
    if len(parts) == 2 and len(parts[1]) != 1:
        return False
    return True
