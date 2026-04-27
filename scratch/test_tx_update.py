from dali.in_transaction import InTransaction
from dali.configuration import Keyword

def test_tx_update():
    tx = InTransaction(
        plugin="test",
        unique_id="1",
        raw_data="raw",
        timestamp="2023-01-01 12:00:00+00:00",
        asset="BTC",
        exchange="Binance",
        holder="Juan",
        transaction_type="BUY",
        spot_price="__unknown",
        crypto_in="1.0"
    )
    
    print(f"Before: {tx.constructor_parameter_dictionary['spot_price']}")
    
    # Update via dict
    tx.constructor_parameter_dictionary['spot_price'] = "50000.0"
    
    print(f"After: {tx.constructor_parameter_dictionary['spot_price']}")

if __name__ == "__main__":
    test_tx_update()
