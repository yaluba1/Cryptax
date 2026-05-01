"""
Service for executing the DaLI tool.
Generates the configuration file and runs the DaLI command.
"""

import subprocess
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Optional, Dict
import configparser
import json
import ccxt
import functools
from dali.plugin.input.rest.binance_com import InputPlugin as BinancePlugin
from dali.plugin.input.rest.kraken import InputPlugin as KrakenPlugin
from dali.in_transaction import InTransaction
from dali.out_transaction import OutTransaction

# Monkey-patching InTransaction to fix a bug in DaLI's Kraken plugin 
# where both crypto_fee and fiat_fee are sometimes provided as "0", which crashes RP2.
def _patch_in_transaction_fees():
    original_init = InTransaction.__init__
    
    @functools.wraps(original_init)
    def patched_init(self, *args, **kwargs):
        # Check if both crypto_fee and fiat_fee are in kwargs
        # (DaLI plugins usually call with named arguments)
        c_fee = kwargs.get('crypto_fee')
        f_fee = kwargs.get('fiat_fee')
        
        if c_fee is not None and f_fee is not None:
            try:
                # If both are zero, or if crypto_fee is zero and fiat_fee is provided,
                # make crypto_fee None to satisfy InTransaction's RP2 validation.
                if float(c_fee) == 0:
                    kwargs['crypto_fee'] = None
            except:
                pass
        original_init(self, *args, **kwargs)
    InTransaction.__init__ = patched_init

_patch_in_transaction_fees()
from dali.ods_generator import generate_input_file
from dali.configuration_generator import generate_configuration_file
from dali.transaction_resolver import resolve_transactions
from dali.abstract_transaction import AbstractTransaction
from dali.intra_transaction import IntraTransaction
from dali.in_transaction import InTransaction
from dali.out_transaction import OutTransaction
from dali.configuration import Keyword, DEFAULT_CONFIGURATION
from worker.config import settings
from worker.logging_config import logger

class DaliService:
    @staticmethod
    def generate_config(
        job_dir: Path,
        account_holder: str,
        exchange: str,
        api_key: str,
        api_secret: str,
        native_fiat: str
    ) -> Path:
        """
        Generates a DaLI .ini configuration file for the specific job.
        """
        config = configparser.ConfigParser()
        
        # For now we support binance and kraken
        if exchange.lower() == 'binance':
            plugin_section = 'dali.plugin.input.rest.binance_com'
            config[plugin_section] = {
                'account_holder': account_holder,
                'api_key': api_key,
                'api_secret': api_secret,
                'native_fiat': native_fiat.upper()
            }
            pair_converter_section = 'dali.plugin.pair_converter.ccxt_binance'
        elif exchange.lower() == 'kraken':
            plugin_section = 'dali.plugin.input.rest.kraken'
            config[plugin_section] = {
                'account_holder': account_holder,
                'api_key': api_key,
                'api_secret': api_secret,
                'native_fiat': native_fiat.upper()
            }
            pair_converter_section = 'dali.plugin.pair_converter.ccxt_kraken'
        else:
            raise ValueError(f"Exchange '{exchange}' not supported yet in DaLI service.")
            
        # Explicitly configure CCXT
        config[pair_converter_section] = {
            'historical_price_type': 'high'
        }
            
        config_path = job_dir / "dali.ini"
        with open(config_path, 'w') as configfile:
            config.write(configfile)
            
        logger.debug("DaLI config generated at {}", config_path)
        return config_path

    @staticmethod
    def get_binance_transactions(
        account_holder: str,
        api_key: str,
        api_secret: str,
        native_fiat: str,
        country_code: str,
        job_dir: Path
    ):
        """
        Loads transactions directly from Binance using the DaLI plugin.
        """
        # Monkey-patch DaLI's cache directory to be job-specific
        import dali.cache
        dali.cache.CACHE_DIR = str(job_dir / ".dali_cache")

        from rp2.plugin.country.es import ES
        # For now we only support ES, but we can generalize later
        if country_code.upper() == 'ES':
            country_obj = ES()
        else:
            country_obj = ES()

        plugin = BinancePlugin(
            account_holder=account_holder,
            api_key=api_key,
            api_secret=api_secret,
            native_fiat=native_fiat.upper()
        )
        
        logger.info("Fetching transactions from Binance REST API for {}...", account_holder)
        return plugin.load(country_obj)

    @staticmethod
    def get_kraken_transactions(
        account_holder: str,
        api_key: str,
        api_secret: str,
        native_fiat: str,
        country_code: str,
        job_dir: Path
    ):
        """
        Loads transactions directly from Kraken using the DaLI plugin.
        """
        # Monkey-patch DaLI's cache directory to be job-specific
        import dali.cache
        dali.cache.CACHE_DIR = str(job_dir / ".dali_cache")
        
        from rp2.plugin.country.es import ES
        # For now we only support ES
        if country_code.upper() == 'ES':
            country_obj = ES()
        else:
            country_obj = ES()

        plugin = KrakenPlugin(
            account_holder=account_holder,
            api_key=api_key,
            api_secret=api_secret,
            native_fiat=native_fiat.upper(),
            use_cache=True # Use local cache to speed up subsequent runs
        )
        
        # Initialize markets to populate base_id_to_base
        plugin._initialize_markets()
        
        # Replace base_id_to_base with a fail-safe dictionary to prevent KeyErrors
        # for unknown internal Kraken IDs (like XETH.B)
        class FailSafeDict(dict):
            def __getitem__(self, key):
                try:
                    return super().__getitem__(key)
                except KeyError:
                    # Fallback to key itself, but strip 'X' or 'Z' prefix if it looks like a legacy ID
                    # Kraken legacy IDs are 4 chars starting with X or Z (e.g. XXBT, ZEUR)
                    if len(key) == 4 and key[0] in ['X', 'Z']:
                        return key[1:]
                    return key

        plugin.base_id_to_base = FailSafeDict(plugin.base_id_to_base)
        
        # Still add specific mappings we know about
        plugin.base_id_to_base.update({
            'XETH.B': 'ETH.B',
            'XETH': 'ETH',
            'XXBT': 'BTC',
            'ZEUR': 'EUR',
            'ZUSD': 'USD',
        })

        # Fail-safe for markets_by_id to avoid KeyErrors on delisted/legacy pairs (e.g. ICXETH)
        class MarketFailSafeDict(dict):
            def __getitem__(self, key):
                try:
                    return super().__getitem__(key)
                except KeyError:
                    # Attempt to guess base/quote from common patterns if not found
                    # Kraken pairs are often BASEQUOTE. Try to split by known quote assets.
                    quotes = ['EUR', 'USD', 'ETH', 'BTC', 'USDT', 'GBP', 'CAD', 'JPY', 'AUD',
                             'ZEUR', 'ZUSD', 'ZGBP', 'ZCAD', 'ZJPY', 'ZAUD', 'XETH', 'XXBT']
                    for quote in quotes:
                        if key.endswith(quote):
                            base = key[:-len(quote)]
                            if base:
                                return [{'id': key, 'baseId': base, 'base': base, 'quote': quote}]
                    
                    # If we can't guess, return a minimal dummy to avoid crash
                    # This might lead to 'UNKNOWN' asset but better than crashing
                    return [{'id': key, 'baseId': key, 'base': key, 'quote': 'UNKNOWN'}]

        plugin._client.markets_by_id = MarketFailSafeDict(plugin._client.markets_by_id)
        
        logger.info("Fetching transactions from Kraken REST API for {}...", account_holder)
        return plugin.load(country_obj)

    @staticmethod
    def enrich_transactions_with_prices(transactions, native_fiat: str, exchange_name: str = 'binance'):
        """
        Enriches transactions with historical prices via CCXT.
        Implements robust retries, bridge currency support, and a persistent Redis cache.
        """
        exchange_name = exchange_name.lower()
        logger.info("Enriching {} transactions with {} prices...", len(transactions), exchange_name)
        
        # Initialize exchange
        if exchange_name == 'kraken':
            exchange = ccxt.kraken({
                'enableRateLimit': True,
                'timeout': 30000,
            })
            request_delay = 1.5 
        else:
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            request_delay = 0.5
        
        native_fiat = native_fiat.upper()
        
        # Helper for fetching with retries
        def fetch_ohlcv_safe(symbol, ts):
            time.sleep(request_delay)
            for attempt in range(5):
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', since=ts, limit=1)
                    return ohlcv
                except ccxt.RateLimitExceeded as e:
                    wait = (attempt + 1) * 5
                    logger.warning("Rate limit exceeded for {} (attempt {}). Waiting {}s...", symbol, attempt+1, wait)
                    time.sleep(wait)
                except (ccxt.NetworkError) as e:
                    if "Too many requests" in str(e):
                        wait = (attempt + 1) * 10
                        time.sleep(wait)
                        continue
                    wait = (attempt + 1) * 2
                    logger.warning("Transient network error for {} (attempt {}): {}. Waiting {}s...", symbol, attempt+1, str(e), wait)
                    time.sleep(wait)
                except ccxt.BadSymbol:
                    return None
                except Exception as e:
                    if "Too many requests" in str(e):
                        wait = (attempt + 1) * 10
                        time.sleep(wait)
                        continue
                    logger.error("Unexpected error fetching {}: {}", symbol, str(e))
                    return None
            return None

        new_prices_count = 0
        for tx in transactions:
            params = tx.constructor_parameter_dictionary
            current_price = params.get(Keyword.SPOT_PRICE.value)
            
            if current_price is None or str(current_price).lower() in [Keyword.UNKNOWN.value, 'none', 'nan', '']:
                asset = tx.asset.upper()
                ts_ms = int(tx.timestamp_value.timestamp() * 1000)
                hour_ts = (ts_ms // 3600000) * 3600000
                
                cached_price = DaliService._get_cached_price(exchange_name, asset, hour_ts)
                if cached_price:
                    DaliService._update_tx_attribute(tx, Keyword.SPOT_PRICE.value, str(cached_price))
                
                # --- STRATEGY -1: Calculate from existing fiat/crypto ---
                calc_price = None
                if isinstance(tx, InTransaction) and tx.fiat_in_no_fee is not None and tx.crypto_in:
                    try:
                        f_val = float(tx.fiat_in_no_fee)
                        c_val = float(tx.crypto_in)
                        if c_val > 0 and f_val > 0:
                            calc_price = str(f_val / c_val)
                    except:
                        pass
                elif isinstance(tx, OutTransaction) and tx.fiat_out_no_fee is not None and tx.crypto_out_no_fee:
                    try:
                        f_val = float(tx.fiat_out_no_fee)
                        c_val = float(tx.crypto_out_no_fee)
                        if c_val > 0 and f_val > 0:
                            calc_price = str(f_val / c_val)
                    except:
                        pass
                
                if calc_price:
                    DaliService._update_tx_attribute(tx, Keyword.SPOT_PRICE.value, calc_price)
                    if not cached_price:
                        DaliService._save_cached_price(exchange_name, asset, hour_ts, float(calc_price))
                        new_prices_count += 1
                    continue

                if cached_price:
                    continue
                
                price = None
                # --- STRATEGY 0: Fiat to Fiat ---
                if asset == native_fiat or (asset in ['ZEUR', 'EUR', 'ZUSD', 'USD'] and asset[1:] == native_fiat):
                    price = "1.0"
                
                # --- STRATEGY 1: Direct Pair ---
                if price is None:
                    symbol = f"{asset}/{native_fiat}"
                    ohlcv = fetch_ohlcv_safe(symbol, hour_ts)
                    if ohlcv and len(ohlcv) > 0:
                        price = str(ohlcv[0][4])
                    if price is None:
                        clean_asset = asset
                        for suffix in ['.S', '.F', '.P', '.B']:
                            if asset.endswith(suffix):
                                clean_asset = asset[:-2]
                                break
                        if clean_asset != asset:
                            symbol = f"{clean_asset}/{native_fiat}"
                            ohlcv = fetch_ohlcv_safe(symbol, hour_ts)
                            if ohlcv and len(ohlcv) > 0:
                                price = str(ohlcv[0][4])
                                asset = clean_asset 
                
                # --- STRATEGY 2: Inverted Pair ---
                if price is None:
                    inv_symbol = f"{native_fiat}/{asset}"
                    ohlcv = fetch_ohlcv_safe(inv_symbol, hour_ts)
                    if ohlcv and len(ohlcv) > 0:
                        price = str(1.0 / float(ohlcv[0][4]))

                # --- STRATEGY 3: Bridge via USDT ---
                if price is None and asset != "USDT":
                    asset_usdt_sym = f"{asset}/USDT"
                    ohlcv_asset = fetch_ohlcv_safe(asset_usdt_sym, hour_ts)
                    usdt_fiat_sym = f"USDT/{native_fiat}"
                    ohlcv_fiat = fetch_ohlcv_safe(usdt_fiat_sym, hour_ts)
                    if not ohlcv_fiat:
                        fiat_usdt_sym = f"{native_fiat}/USDT"
                        ohlcv_fiat_inv = fetch_ohlcv_safe(fiat_usdt_sym, hour_ts)
                        usdt_price_fiat = (1.0 / float(ohlcv_fiat_inv[0][4])) if ohlcv_fiat_inv else None
                    else:
                        usdt_price_fiat = float(ohlcv_fiat[0][4])
                    if ohlcv_asset and usdt_price_fiat:
                        price = str(float(ohlcv_asset[0][4]) * usdt_price_fiat)

                if price:
                    DaliService._update_tx_attribute(tx, Keyword.SPOT_PRICE.value, price)
                    DaliService._save_cached_price(exchange_name, asset, hour_ts, float(price))
                    new_prices_count += 1
                else:
                    logger.warning("No price found for {}/{} on {} at {}. Falling back to 0.0000000001", asset, native_fiat, exchange_name, tx.timestamp_value)
                    DaliService._update_tx_attribute(tx, Keyword.SPOT_PRICE.value, "0.0000000001")

        if new_prices_count > 0:
            logger.info("Added {} new prices to Redis cache.", new_prices_count)

    @staticmethod
    def resolve_and_save(job_dir: Path, transactions, native_fiat: str, exchange: str, account_holder: str):
        """
        Performs the final DaLI steps: resolving transactions and generating 
        the output .ini and .ods files for RP2.
        """
        logger.info("Resolving transactions and generating final output files...")
        config = DEFAULT_CONFIGURATION.copy()
        config[Keyword.NATIVE_FIAT.value] = native_fiat.upper()
        config[Keyword.HISTORICAL_PAIR_CONVERTERS.value] = []
        
        resolved_transactions = resolve_transactions(transactions, config, False)
        warnings = DaliService._cleanup_unknown_values(resolved_transactions, job_dir, exchange, account_holder)
        continuity_warnings = DaliService._ensure_balance_continuity(resolved_transactions, account_holder)
        warnings.extend(continuity_warnings)
        
        generate_configuration_file(
            output_dir_path=str(job_dir),
            output_file_prefix="",
            output_file_name="crypto_data.ini",
            transactions=resolved_transactions,
            global_configuration=config
        )
        generate_input_file(
            output_dir_path=str(job_dir),
            output_file_prefix="",
            output_file_name="crypto_data.ods",
            transactions=resolved_transactions,
            global_configuration=config
        )
        return True

    @staticmethod
    def _update_tx_attribute(tx, field_name: str, value: Any):
        tx.constructor_parameter_dictionary[field_name] = value
        if field_name in [Keyword.ASSET.value, Keyword.NOTES.value, Keyword.TIMESTAMP.value, Keyword.UNIQUE_ID.value]:
            attr_name = f"_AbstractTransaction__{field_name}"
        else:
            class_name = tx.__class__.__name__
            attr_name = f"_{class_name}__{field_name}"
        if hasattr(tx, attr_name):
            setattr(tx, attr_name, value)
        else:
            for attr in [f"_{field_name}", field_name]:
                if hasattr(tx, attr):
                    if not isinstance(getattr(tx.__class__, attr, None), property):
                        setattr(tx, attr, value)

    @staticmethod
    def _cleanup_unknown_values(transactions: List[AbstractTransaction], job_dir: Path, default_exchange: str, default_holder: str) -> List[str]:
        warnings = []
        if not transactions:
            return warnings
        logger.info("Cleaning up {} transactions for RP2 compatibility...", len(transactions))
        unknown_val = Keyword.UNKNOWN.value.lower()
        tiny_val = "0.00000001"

        for tx in transactions:
            tx_modified = False
            params = tx.constructor_parameter_dictionary
            exchange_1 = default_exchange if default_exchange and default_exchange != unknown_val else "Unknown_Exchange_1"
            exchange_2 = "Unknown_Exchange_2"
            
            asset_val = str(params.get(Keyword.ASSET.value, "")).lower()
            if asset_val == unknown_val or not asset_val:
                DaliService._update_tx_attribute(tx, Keyword.ASSET.value, "Unknown_asset")
                tx_modified = True
            elif " " in tx.asset:
                DaliService._update_tx_attribute(tx, Keyword.ASSET.value, tx.asset.replace(" ", "_"))
                tx_modified = True

            if isinstance(tx, (InTransaction, OutTransaction)):
                if str(params.get(Keyword.EXCHANGE.value, "")).lower() == unknown_val:
                    DaliService._update_tx_attribute(tx, Keyword.EXCHANGE.value, exchange_1)
                    tx_modified = True
                if str(params.get(Keyword.HOLDER.value, "")).lower() == unknown_val:
                    DaliService._update_tx_attribute(tx, Keyword.HOLDER.value, default_holder)
                    tx_modified = True
            elif isinstance(tx, IntraTransaction):
                if str(params.get(Keyword.FROM_EXCHANGE.value, "")).lower() == unknown_val:
                    DaliService._update_tx_attribute(tx, Keyword.FROM_EXCHANGE.value, exchange_1)
                    tx_modified = True
                if str(params.get(Keyword.TO_EXCHANGE.value, "")).lower() == unknown_val:
                    DaliService._update_tx_attribute(tx, Keyword.TO_EXCHANGE.value, exchange_2)
                    tx_modified = True
                for field in [Keyword.FROM_HOLDER.value, Keyword.TO_HOLDER.value]:
                    if str(params.get(field, "")).lower() == unknown_val:
                        DaliService._update_tx_attribute(tx, field, default_holder)
                        tx_modified = True

            try:
                if not tx.spot_price or float(tx.spot_price) <= 0:
                    DaliService._update_tx_attribute(tx, Keyword.SPOT_PRICE.value, tiny_val)
                    tx_modified = True
            except:
                DaliService._update_tx_attribute(tx, Keyword.SPOT_PRICE.value, tiny_val)
                tx_modified = True

            if isinstance(tx, InTransaction):
                try:
                    if float(tx.crypto_in) <= 0:
                        DaliService._update_tx_attribute(tx, Keyword.CRYPTO_IN.value, tiny_val)
                        tx_modified = True
                except:
                    DaliService._update_tx_attribute(tx, Keyword.CRYPTO_IN.value, tiny_val)
                    tx_modified = True
                try:
                    if str(params.get(Keyword.CRYPTO_FEE.value)).lower() == unknown_val:
                        DaliService._update_tx_attribute(tx, Keyword.CRYPTO_FEE.value, "0")
                        tx_modified = True
                    if str(params.get(Keyword.FIAT_FEE.value)).lower() == unknown_val:
                        DaliService._update_tx_attribute(tx, Keyword.FIAT_FEE.value, "0")
                        tx_modified = True
                    if tx.fiat_in_no_fee is not None and float(tx.fiat_in_no_fee) <= 0:
                        DaliService._update_tx_attribute(tx, Keyword.FIAT_IN_NO_FEE.value, tiny_val)
                        tx_modified = True
                except: pass
            elif isinstance(tx, OutTransaction):
                try:
                    if float(tx.crypto_out_no_fee) <= 0:
                        DaliService._update_tx_attribute(tx, Keyword.CRYPTO_OUT_NO_FEE.value, tiny_val)
                        tx_modified = True
                    if tx.fiat_out_no_fee is not None and float(tx.fiat_out_no_fee) <= 0:
                        DaliService._update_tx_attribute(tx, Keyword.FIAT_OUT_NO_FEE.value, tiny_val)
                        tx_modified = True
                    if str(params.get(Keyword.CRYPTO_FEE.value)).lower() == unknown_val:
                        DaliService._update_tx_attribute(tx, Keyword.CRYPTO_FEE.value, "0")
                        tx_modified = True
                    if str(params.get(Keyword.FIAT_FEE.value)).lower() == unknown_val:
                        DaliService._update_tx_attribute(tx, Keyword.FIAT_FEE.value, "0")
                        tx_modified = True
                    try:
                        c_fee = float(params.get(Keyword.CRYPTO_FEE.value, 0))
                        f_fee = float(params.get(Keyword.FIAT_FEE.value, 0))
                        s_price = float(tx.spot_price)
                        if f_fee > 0 and c_fee <= 0 and s_price > 0:
                            new_c_fee = f_fee / s_price
                            DaliService._update_tx_attribute(tx, Keyword.CRYPTO_FEE.value, str(new_c_fee))
                            tx_modified = True
                    except: pass
                    try:
                        c_no_fee = float(tx.crypto_out_no_fee)
                        c_fee = float(tx.crypto_fee)
                        c_with_fee_attr = params.get(Keyword.CRYPTO_OUT_WITH_FEE.value)
                        if c_with_fee_attr is not None:
                            c_with_fee = float(c_with_fee_attr)
                            if abs(c_with_fee - (c_no_fee + c_fee)) > 1e-6:
                                DaliService._update_tx_attribute(tx, Keyword.CRYPTO_OUT_WITH_FEE.value, None)
                                tx_modified = True
                    except: pass
                except:
                    DaliService._update_tx_attribute(tx, Keyword.CRYPTO_OUT_NO_FEE.value, tiny_val)
                    tx_modified = True
            elif isinstance(tx, IntraTransaction):
                try:
                    sent_str = str(params.get(Keyword.CRYPTO_SENT.value, ""))
                    recv_str = str(params.get(Keyword.CRYPTO_RECEIVED.value, ""))
                    sent = float(sent_str) if sent_str and sent_str.lower() != unknown_val else 0.0
                    recv = float(recv_str) if recv_str and recv_str.lower() != unknown_val else 0.0
                    if sent <= 0:
                        sent = recv if recv > 0 else float(tiny_val)
                        DaliService._update_tx_attribute(tx, Keyword.CRYPTO_SENT.value, str(sent))
                        tx_modified = True
                    if recv <= 0:
                        recv = sent
                        DaliService._update_tx_attribute(tx, Keyword.CRYPTO_RECEIVED.value, str(recv))
                        tx_modified = True
                    if sent < recv:
                        DaliService._update_tx_attribute(tx, Keyword.CRYPTO_RECEIVED.value, str(sent))
                        tx_modified = True
                except Exception as e:
                    DaliService._update_tx_attribute(tx, Keyword.CRYPTO_SENT.value, tiny_val)
                    DaliService._update_tx_attribute(tx, Keyword.CRYPTO_RECEIVED.value, tiny_val)
                    tx_modified = True

            if tx_modified:
                current_notes = params.get(Keyword.NOTES.value, "") or ""
                if "sanitized" not in str(current_notes).lower():
                    new_notes = f"{current_notes}; Warning: sanitized for RP2".strip("; ")
                    DaliService._update_tx_attribute(tx, Keyword.NOTES.value, new_notes)
                warnings.append(f"Sanitized transaction {tx.unique_id}")

        if warnings:
            warnings_path = job_dir / "warnings.txt"
            with open(warnings_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- Cleanup Pass at {datetime.now()} ---\n")
                for w in warnings: f.write(f"{w}\n")
        return warnings

    @staticmethod
    def _ensure_balance_continuity(transactions: List[AbstractTransaction], default_holder: str) -> List[str]:
        warnings = []
        if not transactions: return warnings
        def sort_key(tx):
            type_order = 2
            if isinstance(tx, InTransaction): type_order = 0
            elif isinstance(tx, IntraTransaction): type_order = 1
            return (tx.timestamp_value, type_order)
        transactions.sort(key=sort_key)
        balances = {} 
        new_transactions = []
        for tx in transactions:
            accounts_to_check = []
            asset = tx.asset
            try:
                if isinstance(tx, InTransaction):
                    accounts_to_check.append((tx.exchange, tx.holder, asset, float(tx.crypto_in)))
                elif isinstance(tx, OutTransaction):
                    if tx.crypto_out_with_fee is not None: total_out = float(tx.crypto_out_with_fee)
                    else: total_out = float(tx.crypto_out_no_fee) + float(tx.crypto_fee)
                    accounts_to_check.append((tx.exchange, tx.holder, asset, -total_out))
                elif isinstance(tx, IntraTransaction):
                    sent = float(tx.crypto_sent)
                    received = float(tx.crypto_received)
                    accounts_to_check.append((tx.from_exchange, tx.from_holder, asset, -sent))
                    accounts_to_check.append((tx.to_exchange, tx.to_holder, asset, received))
            except: continue
            for exchange, holder, asset, change in accounts_to_check:
                key = (exchange, holder, asset)
                if key not in balances: balances[key] = 0.0
                if balances[key] + change < -1e-12:
                    deficit = abs(balances[key] + change)
                    synthetic_dt = tx.timestamp_value - timedelta(seconds=1)
                    synthetic_ts = synthetic_dt.strftime("%Y-%m-%d %H:%M:%S+0000")
                    try: spot_price = tx.spot_price if float(tx.spot_price) > 0 else "0.00000001"
                    except: spot_price = "0.00000001"
                    synthetic_tx = InTransaction(
                        plugin="CrypTax_Recovery",
                        unique_id=f"recovery_{tx.unique_id[:12]}_{exchange[:4]}",
                        raw_data="Synthetic recovery transaction",
                        timestamp=synthetic_ts,
                        asset=asset,
                        exchange=exchange,
                        holder=holder,
                        transaction_type=Keyword.BUY.value.capitalize(),
                        spot_price=str(spot_price),
                        crypto_in=str(deficit),
                        notes=f"Synthetic recovery for {asset} deficit"
                    )
                    new_transactions.append(synthetic_tx)
                    balances[key] += deficit
                    logger.warning("Deficit detected in {}/{} for {}: Injecting {} recovery.", exchange, holder, asset, deficit)
                    warnings.append(f"Account {exchange}/{holder} ({asset}): Injected {deficit} to cover deficit at {synthetic_ts}.")
                balances[key] += change
        if new_transactions:
            transactions.extend(new_transactions)
            transactions.sort(key=sort_key)
        return warnings

    @staticmethod
    def run_dali(country: str, config_path: Path, output_dir: Path, use_spot_lookup: bool = True) -> bool:
        logger.info("Starting DaLI execution for country: {}", country)
        country_code = country.lower()
        binary = "dali_generic" if country_code == "generic" else f"dali_{country_code}"
        try:
            cmd = [binary, "-o", str(output_dir)]
            if use_spot_lookup: cmd.append("-s")
            cmd.append(str(config_path))
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error("DaLI failed code {}. Error: {}", result.returncode, result.stderr)
                return False
            if not (output_dir / "crypto_data.ini").exists() or not (output_dir / "crypto_data.ods").exists():
                return False
            return True
        except Exception as e:
            logger.error("DaLI execution error: {}", e)
            return False
        finally: DaliService._move_logs()

    @staticmethod
    def _move_logs():
        src_dir, dest_dir = Path("./log"), Path("./logs/rp2")
        if not src_dir.exists(): return
        time.sleep(0.5)
        dest_dir.mkdir(parents=True, exist_ok=True)
        for log_file in src_dir.glob("rp2_*.log"):
            try: shutil.move(str(log_file), str(dest_dir / log_file.name))
            except: pass

    @staticmethod
    def _get_redis_conn():
        import redis
        return redis.Redis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db, decode_responses=True)

    @staticmethod
    def _load_price_cache(): return {}

    @staticmethod
    def _get_cached_price(exchange, symbol, timestamp):
        try:
            r = DaliService._get_redis_conn()
            val = r.get(f"cryptax:prices:{exchange}:{symbol}:{timestamp}")
            return float(val) if val else None
        except: return None

    @staticmethod
    def _save_cached_price(exchange, symbol, timestamp, price):
        try:
            r = DaliService._get_redis_conn()
            r.setex(f"cryptax:prices:{exchange}:{symbol}:{timestamp}", 3600 * 24 * 30, str(price))
        except: pass

    @staticmethod
    def _save_price_cache(cache): pass

dali_service = DaliService()
