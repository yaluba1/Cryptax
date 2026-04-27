import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from dali.in_transaction import InTransaction
from dali.configuration import Keyword
from worker.services.dali_service import DaliService

def test_enrich_transactions_with_prices():
    # Create a mock transaction with __unknown price
    tx = InTransaction(
        plugin="test",
        unique_id="1",
        raw_data="raw",
        timestamp="2023-10-01 12:00:00+00:00",
        asset="BTC",
        exchange="Binance",
        holder="Juan",
        transaction_type="BUY",
        spot_price="__unknown",
        crypto_in="1.0"
    )
    
    transactions = [tx]
    
    # Mock CCXT Binance
    with patch('ccxt.binance') as mock_binance:
        mock_exchange = MagicMock()
        mock_binance.return_value = mock_exchange
        
        # Mock fetch_ohlcv returning 50000.0 as close price for BTC/EUR
        mock_exchange.fetch_ohlcv.return_value = [[0, 0, 0, 0, 50000.0, 0]]
        
        DaliService.enrich_transactions_with_prices(transactions, "EUR")
        
        # Check if price was updated
        assert tx.constructor_parameter_dictionary[Keyword.SPOT_PRICE.value] == "50000.0"

def test_enrich_transactions_fallback_price():
    # Create a mock transaction with unknown asset
    tx = InTransaction(
        plugin="test", unique_id="1", raw_data="raw", timestamp="2023-10-01 12:00:00+00:00",
        asset="UNKNOWN_TOKEN", exchange="Binance", holder="Juan", transaction_type="BUY",
        spot_price="__unknown", crypto_in="1.0"
    )
    transactions = [tx]
    
    with patch('ccxt.binance') as mock_binance:
        mock_exchange = MagicMock()
        mock_binance.return_value = mock_exchange
        
        # All calls fail
        mock_exchange.fetch_ohlcv.side_effect = Exception("Symbol not found")
        
        DaliService.enrich_transactions_with_prices(transactions, "EUR")
        
        # Should fallback to 0.0000000001
        assert tx.constructor_parameter_dictionary[Keyword.SPOT_PRICE.value] == "0.0000000001"

def test_resolve_and_save(tmp_path):
    job_dir = tmp_path
    native_fiat = "EUR"
    
    # Mock transactions
    tx = InTransaction(
        plugin="test", unique_id="1", raw_data="raw", timestamp="2023-10-01 12:00:00+00:00",
        asset="BTC", exchange="Binance", holder="Juan", transaction_type="BUY",
        spot_price="50000.0", crypto_in="1.0"
    )
    
    with patch('worker.services.dali_service.resolve_transactions') as mock_resolve:
        mock_resolve.return_value = [tx]
        
        success = DaliService.resolve_and_save(job_dir, [tx], native_fiat)
        
        assert success is True
        assert (job_dir / "crypto_data.ini").exists()
        assert (job_dir / "crypto_data.ods").exists()

def test_cleanup_unknown_values(tmp_path):
    from dali.intra_transaction import IntraTransaction
    from dali.in_transaction import InTransaction
    
    job_dir = tmp_path
    
    # Mock IntraTransaction with unknown crypto_received (this is allowed by the constructor)
    tx_intra = IntraTransaction(
        plugin="test", unique_id="1", raw_data="raw", timestamp="2023-10-01 12:00:00+00:00",
        asset="BNB", from_exchange="Binance", from_holder="Juan",
        to_exchange="__unknown", to_holder="__unknown",
        spot_price="500.0", crypto_sent="10.0", crypto_received="__unknown"
    )
    
    # For InTransaction, crypto_fee doesn't allow __unknown in constructor, 
    # but it might end up there after some DaLI processing or if we manually set it 
    # to simulate the problematic state.
    tx_in = InTransaction(
        plugin="test", unique_id="2", raw_data="raw", timestamp="2023-10-01 12:00:00+00:00",
        asset="BTC", exchange="Binance", holder="Juan", transaction_type="BUY",
        spot_price="50000.0", crypto_in="1.0", crypto_fee=None
    )
    # Manually inject __unknown into the parameter dict to simulate the state that crashes RP2
    tx_in.constructor_parameter_dictionary[Keyword.CRYPTO_FEE.value] = "__unknown"
    
    transactions = [tx_intra, tx_in]
    
    DaliService._cleanup_unknown_values(transactions, job_dir)
    
    # Verify IntraTransaction fallback (received = sent)
    assert tx_intra.constructor_parameter_dictionary[Keyword.CRYPTO_RECEIVED.value] == "10.0"
    
    # Verify InTransaction fallback (fee = 0)
    assert tx_in.constructor_parameter_dictionary[Keyword.CRYPTO_FEE.value] == "0"
    
    # Verify warnings.txt
    warnings_path = job_dir / "warnings.txt"
    assert warnings_path.exists()
    content = warnings_path.read_text()
    assert "crypto_received' was unknown, defaulted to 10.0" in content
    assert "crypto_fee' was unknown, defaulted to 0" in content
