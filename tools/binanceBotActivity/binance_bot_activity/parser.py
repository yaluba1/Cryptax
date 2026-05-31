import re
from typing import Tuple, Union

# Regex to match numeric part (including optional scientific notation) followed by currency symbol (letters)
AMOUNT_CURRENCY_PATTERN = re.compile(r"^([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*([a-zA-Z]+)$")

def parse_amount_and_currency(value: Union[str, float, int]) -> Tuple[float, str]:
    """
    Parses a string representing an amount and a currency (e.g. '0.0740000000BNB')
    and returns a tuple (amount_decimal, currency_name).
    
    If the value is already a number or fails to parse, default values are returned.
    """
    if value is None:
        return 0.0, ""
        
    if isinstance(value, (int, float)):
        return float(value), ""
        
    value_str = str(value).strip()
    if not value_str:
        return 0.0, ""
        
    match = AMOUNT_CURRENCY_PATTERN.match(value_str)
    if match:
        amount = float(match.group(1))
        currency = match.group(2)
        return amount, currency
        
    # Fallback to try and extract any numeric prefix
    fallback_match = re.match(r"^([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)", value_str)
    if fallback_match:
        try:
            return float(fallback_match.group(1)), ""
        except ValueError:
            pass
            
    return 0.0, ""
