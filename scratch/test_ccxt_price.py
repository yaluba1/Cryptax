import ccxt
import time
from datetime import datetime

def test_ccxt_price():
    exchange = ccxt.binance()
    symbol = 'BTC/EUR'
    # Use a fixed timestamp for testing
    dt = "2023-10-01 12:00:00"
    timestamp = int(datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
    
    try:
        # Fetch OHLCV for that timestamp
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', since=timestamp, limit=1)
        if ohlcv:
            print(f"Price for {symbol} at {dt}: {ohlcv[0][4]}")
        else:
            print(f"No price found for {symbol} at {dt}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ccxt_price()
