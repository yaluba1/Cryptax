import pytest
import pandas as pd
from datetime import datetime
from tools.binanceBotActivity.binance_bot_activity.accounting import calculate_bot_pl

def test_accounting_methods():
    # Setup standard test scenario
    # BUY 10 units for 100 total (price = 10.0)
    # BUY 10 units for 120 total (price = 12.0)
    # SELL 15 units for 225 total (price = 15.0)
    data = {
        "Side": ["BUY", "BUY", "SELL"],
        "order_amount": [10.0, 10.0, 15.0],
        "total": [100.0, 120.0, 225.0],
        "parsed_time": [
            datetime(2025, 1, 1, 10, 0, 0),
            datetime(2025, 1, 1, 11, 0, 0),
            datetime(2025, 1, 1, 12, 0, 0)
        ],
        "OrderNo": [100, 101, 102]
    }
    df = pd.DataFrame(data)
    
    # FIFO Expectation:
    # 10 matched against first buy at price 10.0: PL = 10 * (15.0 - 10.0) = 50.0
    # 5 matched against second buy at price 12.0: PL = 5 * (15.0 - 12.0) = 15.0
    # Total PL = 65.0
    assert abs(calculate_bot_pl(df, "FIFO") - 65.0) < 1e-9
    
    # LIFO Expectation:
    # 10 matched against latest buy (second) at price 12.0: PL = 10 * (15.0 - 12.0) = 30.0
    # 5 matched against first buy at price 10.0: PL = 5 * (15.0 - 10.0) = 25.0
    # Total PL = 55.0
    assert abs(calculate_bot_pl(df, "LIFO") - 55.0) < 1e-9
    
    # HIFO Expectation:
    # Highest price is 12.0 (second buy): match 10 units: PL = 30.0
    # Next highest is 10.0 (first buy): match 5 units: PL = 25.0
    # Total PL = 55.0
    assert abs(calculate_bot_pl(df, "HIFO") - 55.0) < 1e-9

def test_accounting_methods_hifo_vs_lifo():
    # Setup scenario where HIFO != LIFO
    # BUY 10 units for 120 total (price = 12.0) - First
    # BUY 10 units for 100 total (price = 10.0) - Second
    # SELL 15 units for 225 total (price = 15.0) - Third
    data = {
        "Side": ["BUY", "BUY", "SELL"],
        "order_amount": [10.0, 10.0, 15.0],
        "total": [120.0, 100.0, 225.0],
        "parsed_time": [
            datetime(2025, 1, 1, 10, 0, 0),
            datetime(2025, 1, 1, 11, 0, 0),
            datetime(2025, 1, 1, 12, 0, 0)
        ],
        "OrderNo": [100, 101, 102]
    }
    df = pd.DataFrame(data)
    
    # FIFO:
    # 10 matched against first buy at 12.0 -> 30.0
    # 5 matched against second buy at 10.0 -> 25.0
    # Total = 55.0
    assert abs(calculate_bot_pl(df, "FIFO") - 55.0) < 1e-9
    
    # LIFO:
    # 10 matched against second buy (latest) at 10.0 -> 50.0
    # 5 matched against first buy at 12.0 -> 15.0
    # Total = 65.0
    assert abs(calculate_bot_pl(df, "LIFO") - 65.0) < 1e-9
    
    # HIFO:
    # Highest price is first buy at 12.0 -> match 10 units -> 30.0
    # Next highest is second buy at 10.0 -> match 5 units -> 25.0
    # Total = 55.0
    assert abs(calculate_bot_pl(df, "HIFO") - 55.0) < 1e-9

def test_accounting_unmatched_sell():
    # SELL 10 units for 150 without any BUY
    data = {
        "Side": ["SELL"],
        "order_amount": [10.0],
        "total": [150.0],
        "parsed_time": [datetime(2025, 1, 1, 12, 0, 0)],
        "OrderNo": [100]
    }
    df = pd.DataFrame(data)
    assert abs(calculate_bot_pl(df, "FIFO") - 150.0) < 1e-9

def test_accounting_empty():
    df = pd.DataFrame()
    assert calculate_bot_pl(df, "FIFO") == 0.0
