def is_v1_us_equity_symbol(symbol: str) -> bool:
    """
    Validate whether a string matches the v1 US equity symbol format.
    
    Validation rules: leading/trailing whitespace are ignored and input is case-insensitive; the normalized symbol must be non-empty, at most 10 characters, contain only alphanumeric characters, dots (.), or hyphens (-); it may contain at most one dot, and if a dot is present the suffix (part after the dot) must be exactly one character.
    
    Parameters:
        symbol (str): The input symbol to validate.
    
    Returns:
        `true` if the symbol conforms to the v1 US equity format, `false` otherwise.
    """
    normalized = symbol.strip().upper()
    if not normalized or len(normalized) > 10:
        return False
    if not all(char.isalnum() or char in {".", "-"} for char in normalized):
        return False
    parts = normalized.split(".")
    if len(parts) > 2:
        return False
    if normalized.startswith(".") or any(part == "" for part in parts):
        return False
    if not any(char.isalnum() for char in parts[0]):
        return False
    if len(parts) == 2 and len(parts[1]) != 1:
        return False
    return True
