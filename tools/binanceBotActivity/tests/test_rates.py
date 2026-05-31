import os
import sqlite3
import pytest
from datetime import datetime
from tools.binanceBotActivity.binance_bot_activity.rates import (
    init_db,
    get_cached_rate,
    save_rate_to_cache,
    get_exchange_rate
)

def test_sqlite_cache(tmp_path):
    db_path = os.path.join(tmp_path, "test_rates.db")
    
    # Init database
    init_db(db_path)
    assert os.path.exists(db_path)
    
    # Cache miss
    rate = get_cached_rate(db_path, "frankfurter", "2025-01-01", "USD", "EUR")
    assert rate is None
    
    # Save to cache
    save_rate_to_cache(db_path, "frankfurter", "2025-01-01", "USD", "EUR", 0.925)
    
    # Cache hit
    rate = get_cached_rate(db_path, "frankfurter", "2025-01-01", "USD", "EUR")
    assert rate == 0.925
    
    # Overwrite cache
    save_rate_to_cache(db_path, "frankfurter", "2025-01-01", "USD", "EUR", 0.930)
    rate = get_cached_rate(db_path, "frankfurter", "2025-01-01", "USD", "EUR")
    assert rate == 0.930

def test_same_currency(tmp_path):
    db_path = os.path.join(tmp_path, "test_rates.db")
    dt = datetime(2025, 1, 1, 12, 0, 0)
    
    # Same currency should immediately return 1.0 without querying database or API
    rate = get_exchange_rate(db_path, "EUR", "EUR", dt)
    assert rate == 1.0

def test_get_exchange_rate_fallback(tmp_path):
    db_path = os.path.join(tmp_path, "test_rates.db")
    init_db(db_path)
    
    dt = datetime(2025, 1, 1, 12, 0, 0)
    
    # Query rate (will fetch from Frankfurter or use fallback if offline)
    rate = get_exchange_rate(db_path, "USDC", "EUR", dt)
    assert rate > 0.0
    
    # Verify it got saved to cache with USDC as original currency
    cached = get_cached_rate(db_path, "frankfurter", "2025-01-01", "USDC", "EUR")
    assert cached == rate
