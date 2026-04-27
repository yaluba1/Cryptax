import pytest
import configparser
from pathlib import Path
from worker.services.dali_service import DaliService

def test_generate_config_binance(tmp_path):
    job_dir = tmp_path
    account_holder = "test@example.com"
    exchange = "binance"
    api_key = "test_key"
    api_secret = "test_secret"
    native_fiat = "EUR"
    
    config_path = DaliService.generate_config(
        job_dir, account_holder, exchange, api_key, api_secret, native_fiat
    )
    
    assert config_path.exists()
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # Check input plugin
    assert 'dali.plugin.input.rest.binance_com' in config
    assert config['dali.plugin.input.rest.binance_com']['account_holder'] == account_holder
    assert config['dali.plugin.input.rest.binance_com']['api_key'] == api_key
    assert config['dali.plugin.input.rest.binance_com']['api_secret'] == api_secret
    assert config['dali.plugin.input.rest.binance_com']['native_fiat'] == "EUR"
    
    # Check pair converter plugin
    assert 'dali.plugin.pair_converter.ccxt_binance' in config
    assert config['dali.plugin.pair_converter.ccxt_binance']['historical_price_type'] == 'high'
    assert 'default_exchange' not in config['dali.plugin.pair_converter.ccxt_binance']
    assert 'dali.plugin.pair_converter.ccxt' not in config

def test_generate_config_unsupported(tmp_path):
    with pytest.raises(ValueError, match="Exchange 'kraken' not supported yet"):
        DaliService.generate_config(
            tmp_path, "test@example.com", "kraken", "key", "secret", "USD"
        )
