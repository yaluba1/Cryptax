import ccxt
from dali.plugin.input.rest.binance_com import InputPlugin as BinancePlugin
from dali.configuration import Keyword
import os

def test_binance_plugin():
    # This is just a test to see if we can instantiate and use the plugin
    try:
        plugin = BinancePlugin(
            account_holder="test",
            api_key="key",
            api_secret="secret",
            native_fiat="EUR"
        )
        print("Successfully instantiated BinancePlugin")
    except Exception as e:
        print(f"Error instantiating BinancePlugin: {e}")

if __name__ == "__main__":
    test_binance_plugin()
