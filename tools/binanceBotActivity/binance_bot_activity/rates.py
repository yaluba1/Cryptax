import os
import sqlite3
import urllib.request
import json
import time
from datetime import datetime

# SQLite caching backend
def init_db(db_path: str):
    """Initializes the exchange rates SQLite cache database if it does not exist."""
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exchange_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            date_key TEXT NOT NULL,
            from_curr TEXT NOT NULL,
            to_curr TEXT NOT NULL,
            rate REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, date_key, from_curr, to_curr)
        )
    """)
    conn.commit()
    conn.close()

def get_cached_rate(db_path: str, source: str, date_key: str, from_curr: str, to_curr: str) -> float:
    """Retrieves a cached rate from the database, or None if not found."""
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT rate FROM exchange_rates WHERE source = ? AND date_key = ? AND from_curr = ? AND to_curr = ?",
            (source, date_key, from_curr.upper(), to_curr.upper())
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None

def save_rate_to_cache(db_path: str, source: str, date_key: str, from_curr: str, to_curr: str, rate: float):
    """Saves a fetched rate to the SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO exchange_rates (source, date_key, from_curr, to_curr, rate)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source, date_key, from_curr.upper(), to_curr.upper(), rate)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Failed to save rate to cache: {e}")

def fetch_from_frankfurter(from_curr: str, to_curr: str, date_str: str) -> float:
    """Fetches ECB reference rate from the Frankfurter API for the given date."""
    from_curr = from_curr.upper()
    to_curr = to_curr.upper()
    url = f"https://api.frankfurter.app/{date_str}?from={from_curr}&to={to_curr}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if "rates" in data and to_curr in data["rates"]:
                return float(data["rates"][to_curr])
    except Exception as e:
        print(f"Warning: Frankfurter API query failed for {from_curr}->{to_curr} on {date_str}: {e}")
        
    return None

def fetch_from_binance(from_curr: str, to_curr: str, timestamp_ms: int) -> float:
    """Fetches the 1-minute historical candle rate from Binance public API."""
    from_curr = from_curr.upper()
    to_curr = to_curr.upper()
    
    # Try direct pair first, then inverted pair
    pairs_to_try = [
        (f"{from_curr}{to_curr}", False),
        (f"{to_curr}{from_curr}", True)
    ]
    
    for symbol, invert in pairs_to_try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&startTime={timestamp_ms}&limit=1"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                candles = json.loads(response.read().decode())
                if candles and len(candles) > 0:
                    # kline format: [open_time, open, high, low, close, ...]
                    # We use the close price (index 4) or average of open/close
                    close_price = float(candles[0][4])
                    if close_price > 0.0:
                        rate = 1.0 / close_price if invert else close_price
                        return rate
        except Exception:
            continue
            
    return None

# Global in-memory cache dictionary to avoid heavy sequential SQLite queries
_MEMORY_CACHE = {}

def get_exchange_rate(db_path: str, from_curr: str, to_curr: str, dt_val: datetime) -> float:
    """
    Main function to get exchange rate with caching.
    Supports Frankfurter for EUR and Binance as fallback/general.
    """
    from_curr = from_curr.upper().strip()
    to_curr = to_curr.upper().strip()
    
    if from_curr == to_curr:
        return 1.0
        
    # Standardize stablecoin mappings if needed (e.g. USDC to USD/EUR)
    # If source base is USDC and target is EUR, we can query Frankfurter for USD->EUR
    source_curr = from_curr
    if source_curr == "USDC" and to_curr == "EUR":
        source_curr = "USD"
        
    # Decide source and keys
    is_eur = (to_curr == "EUR")
    if is_eur:
        source = "frankfurter"
        date_key = dt_val.strftime("%Y-%m-%d")
    else:
        source = "binance"
        # Use minute-level resolution for Binance key
        date_key = dt_val.strftime("%Y-%m-%d %H:%M")
        
    # Check in-memory cache first
    cache_key = (source, date_key, from_curr, to_curr)
    if cache_key in _MEMORY_CACHE:
        return _MEMORY_CACHE[cache_key]
        
    # Check database cache next
    cached = get_cached_rate(db_path, source, date_key, from_curr, to_curr)
    if cached is not None:
        _MEMORY_CACHE[cache_key] = cached
        return cached
        
    # Fetch from API
    rate = None
    if source == "frankfurter":
        rate = fetch_from_frankfurter(source_curr, to_curr, date_key)
        # Fallback to Binance if Frankfurter fails
        if rate is None:
            # Convert datetime to millisecond epoch
            timestamp_ms = int(time.mktime(dt_val.timetuple())) * 1000
            rate = fetch_from_binance(from_curr, to_curr, timestamp_ms)
    else:
        timestamp_ms = int(time.mktime(dt_val.timetuple())) * 1000
        rate = fetch_from_binance(from_curr, to_curr, timestamp_ms)
        
    # Fallback default values
    if rate is None:
        # Common stablecoin to fiat fallback estimates in case APIs fail
        if from_curr in ["USDC", "USDT"] and to_curr == "EUR":
            rate = 0.92  # conservative fallback
        else:
            rate = 1.0
            print(f"Warning: Could not fetch rate for {from_curr}->{to_curr} on {date_key}. Using 1.0 as fallback.")
            
    # Save to caches
    save_rate_to_cache(db_path, source, date_key, from_curr, to_curr, rate)
    _MEMORY_CACHE[cache_key] = rate
    return rate
