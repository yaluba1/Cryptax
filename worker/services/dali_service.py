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
import ccxt
from dali.plugin.input.rest.binance_com import InputPlugin as BinancePlugin
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
        
        # Plugin section
        # For now we only support binance (dali.plugin.input.rest.binance_com)
        if exchange.lower() == 'binance':
            plugin_section = 'dali.plugin.input.rest.binance_com'
            config[plugin_section] = {
                'account_holder': account_holder,
                'api_key': api_key,
                'api_secret': api_secret,
                'native_fiat': native_fiat.upper()
            }
        else:
            raise ValueError(f"Exchange '{exchange}' not supported yet in DaLI service.")
            
        # Explicitly configure CCXT to prevent DaLI from loading the broken HistoricCrypto plugin
        # Use ccxt_binance to lock pricing to Binance.com and prevent DaLI from defaulting 
        # to Kraken, which requires downloading a 4.1GB CSV file.
        pair_converter_section = 'dali.plugin.pair_converter.ccxt_binance'
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
        country_code: str
    ):
        """
        Loads transactions directly from Binance using the DaLI plugin.
        """
        from rp2.plugin.country.es import ES
        # For now we only support ES, but we can generalize later
        if country_code.upper() == 'ES':
            country_obj = ES()
        else:
            # Fallback to ES as a safe default for currency/fiat if unknown
            # Ideally we'd have a factory for this
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
    def enrich_transactions_with_prices(transactions, native_fiat: str):
        """
        Enriches transactions with historical prices from Binance via CCXT.
        Implements robust retries and bridge currency support for high reliability.
        """
        logger.info("Enriching {} transactions with Binance prices...", len(transactions))
        # enableRateLimit allows CCXT to manage the request pacing automatically
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        
        # Cache for (asset, fiat, hour_timestamp) -> price
        price_cache = {}
        native_fiat = native_fiat.upper()
        
        # Helper for fetching with retries
        def fetch_ohlcv_safe(symbol, ts):
            for attempt in range(3):
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', since=ts, limit=1)
                    return ohlcv
                except (ccxt.NetworkError, ccxt.RateLimitExceeded) as e:
                    wait = (attempt + 1) * 2
                    logger.warning("Transient error fetching {} (attempt {}): {}. Waiting {}s...", symbol, attempt+1, str(e), wait)
                    time.sleep(wait)
                except ccxt.BadSymbol:
                    return None # Non-existent pair, no point in retrying
                except Exception as e:
                    logger.error("Unexpected error fetching {}: {}", symbol, str(e))
                    return None
            return None

        for tx in transactions:
            params = tx.constructor_parameter_dictionary
            current_price = params.get(Keyword.SPOT_PRICE.value)
            
            # Check if spot price is missing or unknown
            if current_price is None or str(current_price).lower() in [Keyword.UNKNOWN.value, 'none', 'nan', '']:
                asset = tx.asset.upper()
                
                # Use hourly timestamp as cache key
                ts_ms = int(tx.timestamp_value.timestamp() * 1000)
                hour_ts = (ts_ms // 3600000) * 3600000
                cache_key = (asset, native_fiat, hour_ts)
                
                if cache_key in price_cache:
                    DaliService._update_tx_attribute(tx, Keyword.SPOT_PRICE.value, price_cache[cache_key])
                    continue
                
                price = None
                
                # --- STRATEGY 1: Direct Pair (e.g. SOL/EUR) ---
                symbol = f"{asset}/{native_fiat}"
                ohlcv = fetch_ohlcv_safe(symbol, hour_ts)
                if ohlcv and len(ohlcv) > 0:
                    price = str(ohlcv[0][4])
                    logger.debug("Found direct price for {}: {}", symbol, price)
                
                # --- STRATEGY 2: Inverted Pair (e.g. EUR/SOL) ---
                if price is None:
                    inv_symbol = f"{native_fiat}/{asset}"
                    ohlcv = fetch_ohlcv_safe(inv_symbol, hour_ts)
                    if ohlcv and len(ohlcv) > 0:
                        price = str(1.0 / float(ohlcv[0][4]))
                        logger.debug("Found inverted price for {}: {}", inv_symbol, price)

                # --- STRATEGY 3: Bridge via USDT (e.g. SOL/USDT * USDT/EUR) ---
                if price is None and asset != "USDT":
                    # a. Asset to USDT
                    asset_usdt_sym = f"{asset}/USDT"
                    ohlcv_asset = fetch_ohlcv_safe(asset_usdt_sym, hour_ts)
                    
                    # b. USDT to Native Fiat
                    usdt_fiat_sym = f"USDT/{native_fiat}"
                    ohlcv_fiat = fetch_ohlcv_safe(usdt_fiat_sym, hour_ts)
                    
                    # Try inverted fiat if direct fails (e.g. EUR/USDT)
                    if not ohlcv_fiat:
                        fiat_usdt_sym = f"{native_fiat}/USDT"
                        ohlcv_fiat_inv = fetch_ohlcv_safe(fiat_usdt_sym, hour_ts)
                        if ohlcv_fiat_inv:
                            usdt_price_fiat = 1.0 / float(ohlcv_fiat_inv[0][4])
                        else:
                            usdt_price_fiat = None
                    else:
                        usdt_price_fiat = float(ohlcv_fiat[0][4])

                    if ohlcv_asset and usdt_price_fiat:
                        asset_price_usdt = float(ohlcv_asset[0][4])
                        price = str(asset_price_usdt * usdt_price_fiat)
                        logger.debug("Found bridged price for {} via USDT: {}", asset, price)

                # --- FINALIZE ---
                if price:
                    DaliService._update_tx_attribute(tx, Keyword.SPOT_PRICE.value, price)
                    price_cache[cache_key] = price
                else:
                    logger.warning("No price found on Binance for {}/{} at {}. Falling back to 0.0000000001", asset, native_fiat, tx.timestamp_value)
                    DaliService._update_tx_attribute(tx, Keyword.SPOT_PRICE.value, "0.0000000001")
                
                # Small pause to be extra safe with rate limits if we are hammering many new unique hours
                if len(price_cache) % 20 == 0:
                    time.sleep(0.1)

    @staticmethod
    def resolve_and_save(job_dir: Path, transactions, native_fiat: str, exchange: str, account_holder: str):
        """
        Performs the final DaLI steps: resolving transactions and generating 
        the output .ini and .ods files for RP2.
        """
        logger.info("Resolving transactions and generating final output files...")
        
        config = DEFAULT_CONFIGURATION.copy()
        config[Keyword.NATIVE_FIAT.value] = native_fiat.upper()
        # Ensure pair converters list exists even if empty to avoid KeyError in resolver
        config[Keyword.HISTORICAL_PAIR_CONVERTERS.value] = []
        
        # 1. Resolve transactions (merges transfers, etc.)
        resolved_transactions = resolve_transactions(transactions, config, False)
        
        # 2. Cleanup transactions
        warnings = DaliService._cleanup_unknown_values(resolved_transactions, job_dir, exchange, account_holder)
        
        # Ensure balance continuity (inject synthetic buys if needed)
        continuity_warnings = DaliService._ensure_balance_continuity(resolved_transactions, account_holder)
        warnings.extend(continuity_warnings)
        
        # 3. Generate crypto_data.ini
        logger.info("Generating crypto_data.ini...")
        generate_configuration_file(
            output_dir_path=str(job_dir),
            output_file_prefix="",
            output_file_name="crypto_data.ini",
            transactions=resolved_transactions,
            global_configuration=config
        )
        
        # 3. Generate crypto_data.ods
        logger.info("Generating crypto_data.ods...")
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
        """
        Internal helper to update both the constructor dictionary AND the 
        private attributes of a DaLI transaction object. This is necessary 
        because DaLI's INI generator uses properties (which read from private 
        attributes), while its ODS generator uses the constructor dictionary.
        """
        # 1. Update dictionary (used for ODS generation)
        tx.constructor_parameter_dictionary[field_name] = value
        
        # 2. Update private attribute (used for property access during INI generation)
        # Handle AbstractTransaction fields (inherited by all)
        # 2. Update private attribute (used for property access during INI generation)
        # Handle AbstractTransaction fields (inherited by all)
        if field_name in [Keyword.ASSET.value, Keyword.NOTES.value, Keyword.TIMESTAMP.value, Keyword.UNIQUE_ID.value]:
            attr_name = f"_AbstractTransaction__{field_name}"
        else:
            class_name = tx.__class__.__name__
            attr_name = f"_{class_name}__{field_name}"
            
        if hasattr(tx, attr_name):
            setattr(tx, attr_name, value)
        else:
            # Fallback for unexpected cases or non-standard naming
            # We must be careful not to call setattr on properties (which have no setter)
            for attr in [f"_{field_name}", field_name]:
                if hasattr(tx, attr):
                    # Check if it's a property to avoid AttributeError: property '...' has no setter
                    if not isinstance(getattr(tx.__class__, attr, None), property):
                        setattr(tx, attr, value)

    @staticmethod
    @staticmethod
    def _cleanup_unknown_values(transactions: List[AbstractTransaction], job_dir: Path, default_exchange: str, default_holder: str) -> List[str]:
        """
        DaLI can leave some fields as '__unknown' if it can't resolve them.
        RP2 will crash if these are present in critical columns or not in the config.
        This method patches them with sensible defaults and ensures numeric fields are positive.
        """
        warnings = []
        if not transactions:
            return warnings

        logger.info("Cleaning up {} transactions for RP2 compatibility...", len(transactions))
        
        unknown_val = Keyword.UNKNOWN.value.lower()
        tiny_val = "0.00000001"

        for tx in transactions:
            tx_modified = False
            params = tx.constructor_parameter_dictionary
            
            # 1. Basic field cleanup (Strings)
            exchange_1 = default_exchange if default_exchange and default_exchange != unknown_val else "Unknown_Exchange_1"
            exchange_2 = "Unknown_Exchange_2"
            
            # Asset cleanup
            asset_val = str(params.get(Keyword.ASSET.value, "")).lower()
            if asset_val == unknown_val or not asset_val:
                DaliService._update_tx_attribute(tx, Keyword.ASSET.value, "Unknown_asset")
                tx_modified = True
            elif " " in tx.asset:
                DaliService._update_tx_attribute(tx, Keyword.ASSET.value, tx.asset.replace(" ", "_"))
                tx_modified = True

            # Exchange & Holder
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

            # 2. Numeric Robustness (Non-zero constraints)
            # Spot Price
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

            elif isinstance(tx, OutTransaction):
                try:
                    out_val = float(tx.crypto_out_no_fee)
                    fee_val = float(tx.crypto_fee)
                    if out_val <= 0 and fee_val <= 0:
                        DaliService._update_tx_attribute(tx, Keyword.CRYPTO_OUT_NO_FEE.value, tiny_val)
                        tx_modified = True
                except:
                    DaliService._update_tx_attribute(tx, Keyword.CRYPTO_OUT_NO_FEE.value, tiny_val)
                    tx_modified = True

            elif isinstance(tx, IntraTransaction):
                try:
                    # Robust check for sent/received
                    sent_str = str(params.get(Keyword.CRYPTO_SENT.value, ""))
                    recv_str = str(params.get(Keyword.CRYPTO_RECEIVED.value, ""))
                    
                    sent = float(sent_str) if sent_str and sent_str.lower() != unknown_val else 0.0
                    recv = float(recv_str) if recv_str and recv_str.lower() != unknown_val else 0.0

                    if sent <= 0:
                        sent = recv if recv > 0 else float(tiny_val)
                        DaliService._update_tx_attribute(tx, Keyword.CRYPTO_SENT.value, str(sent))
                        tx_modified = True
                    
                    if recv <= 0:
                        # RP2 usually accepts received=0 if it's a fee-only transfer, 
                        # but user asked to set it to sent if zero.
                        recv = sent
                        DaliService._update_tx_attribute(tx, Keyword.CRYPTO_RECEIVED.value, str(recv))
                        tx_modified = True
                        
                    if sent < recv:
                        # Cannot receive more than sent (negative fee)
                        DaliService._update_tx_attribute(tx, Keyword.CRYPTO_RECEIVED.value, str(sent))
                        tx_modified = True
                except Exception as e:
                    logger.warning("IntraTransaction numeric repair failed for {}: {}", tx.unique_id, e)
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
                for w in warnings:
                    f.write(f"{w}\n")
            logger.info("Updated {} with {} cleanup warnings.", warnings_path, len(warnings))
            
        return warnings

    @staticmethod
    def _ensure_balance_continuity(transactions: List[AbstractTransaction], default_holder: str) -> List[str]:
        """
        Detects if an asset balance goes negative (missing history) in ANY account
        and injects synthetic InTransactions to restore continuity and prevent RP2 crashes.
        """
        warnings = []
        if not transactions:
            return warnings

        # 1. Sort transactions by timestamp
        def parse_dt(tx):
            ts = tx.timestamp
            for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S+0000"):
                try:
                    return datetime.strptime(ts, fmt)
                except ValueError:
                    continue
            return datetime.min
        
        transactions.sort(key=parse_dt)
        
        # 2. Track balance PER ACCOUNT (Exchange + Holder + Asset)
        # Key: (exchange, holder, asset)
        balances = {} 
        new_transactions = []
        recovery_exchange = "Missing_Data_Recovery"
        
        for tx in transactions:
            # We must handle both single-account (In/Out) and dual-account (Intra)
            accounts_to_check = [] # List of (exchange, holder, asset, change_val)
            
            asset = tx.asset
            try:
                if isinstance(tx, InTransaction):
                    accounts_to_check.append((tx.exchange, tx.holder, asset, float(tx.crypto_in)))
                elif isinstance(tx, OutTransaction):
                    total_out = float(tx.crypto_out_no_fee) + float(tx.crypto_fee)
                    accounts_to_check.append((tx.exchange, tx.holder, asset, -total_out))
                elif isinstance(tx, IntraTransaction):
                    # Intra impacts TWO accounts
                    sent = float(tx.crypto_sent)
                    received = float(tx.crypto_received)
                    accounts_to_check.append((tx.from_exchange, tx.from_holder, asset, -sent))
                    accounts_to_check.append((tx.to_exchange, tx.to_holder, asset, received))
            except (ValueError, TypeError):
                continue
            
            for exchange, holder, asset, change in accounts_to_check:
                key = (exchange, holder, asset)
                if key not in balances:
                    balances[key] = 0.0
                
                # If this change makes the specific account go negative, recover it
                if balances[key] + change < -1e-9:
                    deficit = abs(balances[key] + change)
                    
                    current_dt = parse_dt(tx)
                    synthetic_dt = current_dt - timedelta(seconds=1)
                    synthetic_ts = synthetic_dt.strftime("%Y-%m-%d %H:%M:%S+0000")
                    
                    try:
                        spot_price = tx.spot_price if float(tx.spot_price) > 0 else "0.00000001"
                    except:
                        spot_price = "0.00000001"
                        
                    synthetic_tx = InTransaction(
                        plugin="CrypTax_Recovery",
                        unique_id=f"recovery_{tx.unique_id[:12]}_{exchange[:4]}",
                        raw_data="Synthetic recovery transaction for missing account history",
                        timestamp=synthetic_ts,
                        asset=asset,
                        exchange=exchange, # Injected exactly where the deficit occurred
                        holder=holder,
                        transaction_type=Keyword.BUY.value.capitalize(),
                        spot_price=str(spot_price),
                        crypto_in=str(deficit),
                        notes=f"Synthetic recovery to cover {asset} deficit in {exchange}"
                    )
                    
                    new_transactions.append(synthetic_tx)
                    balances[key] += deficit
                    warnings.append(f"Account {exchange}/{holder} ({asset}): Injected {deficit} to cover deficit.")
                
                balances[key] += change

        if new_transactions:
            transactions.extend(new_transactions)
            transactions.sort(key=parse_dt)
            
        return warnings

    @staticmethod
    def run_dali(country: str, config_path: Path, output_dir: Path, use_spot_lookup: bool = True) -> bool:
        """
        Executes the DaLI command (e.g., dali_es, dali_generic).
        """
        logger.info("Starting DaLI execution for country: {}", country)
        
        # Determine the binary based on country
        country_code = country.lower()
        if country_code == "generic":
            binary = "dali_generic"
        else:
            binary = f"dali_{country_code}"
            
        try:
            # Command: binary -o <output_dir> [-s] <config_path>
            # We use -s to read spot prices if missing
            cmd = [
                binary,
                "-o", str(output_dir)
            ]
            
            if use_spot_lookup:
                cmd.append("-s")
                
            cmd.append(str(config_path))
            
            logger.debug("Executing command: {}", " ".join(cmd))
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False # We handle return code manually
            )
            
            if result.returncode != 0:
                logger.error("DaLI failed with exit code {}. Error: {}", result.returncode, result.stderr)
                return False
                
            # Verify output files exist
            ini_output = output_dir / "crypto_data.ini"
            ods_output = output_dir / "crypto_data.ods"
            
            if not ini_output.exists() or not ods_output.exists():
                logger.error("DaLI reported success but output files are missing. Output: {}", result.stdout)
                return False
                
            logger.info("DaLI execution completed successfully.")
            logger.debug("DaLI output: {}", result.stdout)
            return True
            
        except FileNotFoundError:
            logger.error("{} command not found. Ensure it is installed in the environment.", binary)
            return False
        except Exception as e:
            logger.error("An error occurred during DaLI execution: {}", str(e))
            return False
        finally:
            # Always attempt to move logs, regardless of success or failure
            DaliService._move_logs()

    @staticmethod
    def _move_logs():
        """
        Moves RP2/DaLI log files from the hardcoded ./log directory 
        to the project's preferred ./logs/rp2 directory.
        """
        import time
        import os
        
        src_dir = Path("./log")
        dest_dir = Path("./logs/rp2")
        
        if not src_dir.exists():
            return
            
        # Small delay to ensure file handles are released by the OS
        time.sleep(0.5)
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        for log_file in src_dir.glob("rp2_*.log"):
            try:
                shutil.move(str(log_file), str(dest_dir / log_file.name))
            except PermissionError as e:
                # Handle WinError 32: File in use
                if os.name == 'nt' and getattr(e, 'winerror', None) == 32:
                    logger.debug("Log file {} is currently in use (possibly by another job), skipping move.", log_file)
                else:
                    logger.warning("Permission error moving log file {}: {}", log_file, str(e))
            except Exception as e:
                logger.warning("Failed to move log file {}: {}", log_file, str(e))

dali_service = DaliService()
