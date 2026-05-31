import pytest
from tools.binanceBotActivity.binance_bot_activity.parser import parse_amount_and_currency

def test_parse_valid_amount_and_currency():
    assert parse_amount_and_currency("0.0740000000BNB") == (0.074, "BNB")
    assert parse_amount_and_currency("69.5836800000USDC") == (69.58368, "USDC")
    assert parse_amount_and_currency("150SOL") == (150.0, "SOL")
    assert parse_amount_and_currency("  0.1990000000SOL  ") == (0.199, "SOL")

def test_parse_scientific_notation():
    assert parse_amount_and_currency("1e-5BTC") == (1e-5, "BTC")
    assert parse_amount_and_currency("2.5e3USD") == (2500.0, "USD")

def test_parse_numeric_only():
    assert parse_amount_and_currency("123.45") == (123.45, "")
    assert parse_amount_and_currency(123.45) == (123.45, "")
    assert parse_amount_and_currency(100) == (100.0, "")

def test_parse_empty_and_invalid():
    assert parse_amount_and_currency("") == (0.0, "")
    assert parse_amount_and_currency(None) == (0.0, "")
    assert parse_amount_and_currency("invalid") == (0.0, "")
    assert parse_amount_and_currency("SOL") == (0.0, "")
