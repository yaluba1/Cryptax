import pandas as pd
from pathlib import Path
from typing import List
from datetime import datetime, timezone
import json

from dali.in_transaction import InTransaction
from dali.out_transaction import OutTransaction
from dali.abstract_transaction import AbstractTransaction
from dali.configuration import Keyword

from tools.binanceBotActivity.binance_bot_activity.cleaner import clean_data
from tools.binanceBotActivity.binance_bot_activity.parser import parse_amount_and_currency
from worker.logging_config import logger

def parse_bot_csv_to_dali_transactions(csv_path: Path, account_holder: str) -> List[AbstractTransaction]:
    """
    Parses a Binance bot activity CSV file and converts each buy/sell trade
    into InTransaction and OutTransaction pairs for double-entry crypto matching in RP2.
    """
    logger.info("Parsing bot CSV file: {}", csv_path)
    
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        logger.error("Failed to read bot CSV {}: {}", csv_path, str(e))
        return []
        
    df_cleaned = clean_data(df)
    if df_cleaned.empty:
        logger.warning("No transactions found in cleaned bot CSV: {}", csv_path)
        return []
        
    transactions: List[AbstractTransaction] = []
    
    for _, row in df_cleaned.iterrows():
        try:
            strategy_id = str(row.get("Strategy_Id", "Unknown"))
            pair = str(row.get("Pair", ""))
            side = str(row.get("Side", "")).upper()
            time_str = str(row.get("Time", ""))
            order_no = str(row.get("OrderNo", ""))
            
            order_amt_raw = row.get("Order Amount", "")
            executed_raw = row.get("Executed", "")
            trading_total_raw = row.get("Trading total", "")
            
            # Parse amounts and currencies
            order_amt, pair_asset = parse_amount_and_currency(order_amt_raw)
            executed, _ = parse_amount_and_currency(executed_raw)
            trading_total, base_asset = parse_amount_and_currency(trading_total_raw)
            
            if not pair_asset or not base_asset or executed <= 0:
                continue
                
            # Convert time to UTC RP2 format: YYYY-MM-DD HH:MM:SS+0000
            try:
                dt = pd.to_datetime(time_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S%z")
            except Exception as te:
                logger.warning("Failed to parse time '{}': {}", time_str, str(te))
                continue
                
            # Calculate execution spot price: base spent/received per pair asset
            spot_price = str(trading_total / executed)
            
            raw_data = json.dumps(row.to_dict())
            
            # double entry crypto-to-crypto trade matching
            if side == "BUY":
                # InTransaction: bought asset (e.g. SOL)
                in_tx = InTransaction(
                    plugin="Binance_Bot",
                    unique_id=f"{order_no}_in",
                    raw_data=raw_data,
                    timestamp=timestamp_str,
                    asset=pair_asset,
                    exchange="Binance",
                    holder=account_holder,
                    transaction_type="Buy",
                    spot_price=spot_price,
                    crypto_in=str(executed),
                    crypto_fee="0",
                    fiat_in_no_fee=None,
                    fiat_in_with_fee=None,
                    fiat_fee=None,
                    notes=f"Binance Bot Buy (Strategy ID: {strategy_id})"
                )
                
                # OutTransaction: spent base currency (e.g. USDC)
                out_tx = OutTransaction(
                    plugin="Binance_Bot",
                    unique_id=f"{order_no}_out",
                    raw_data=raw_data,
                    timestamp=timestamp_str,
                    asset=base_asset,
                    exchange="Binance",
                    holder=account_holder,
                    transaction_type="Sell",
                    spot_price="1.0",
                    crypto_out_no_fee=str(trading_total),
                    crypto_fee="0",
                    crypto_out_with_fee=str(trading_total),
                    fiat_out_no_fee=None,
                    fiat_fee=None,
                    notes=f"Binance Bot Buy Side-Effect (Strategy ID: {strategy_id})"
                )
                
                transactions.append(in_tx)
                transactions.append(out_tx)
                
            elif side == "SELL":
                # OutTransaction: sold asset (e.g. SOL)
                out_tx = OutTransaction(
                    plugin="Binance_Bot",
                    unique_id=f"{order_no}_out",
                    raw_data=raw_data,
                    timestamp=timestamp_str,
                    asset=pair_asset,
                    exchange="Binance",
                    holder=account_holder,
                    transaction_type="Sell",
                    spot_price=spot_price,
                    crypto_out_no_fee=str(executed),
                    crypto_fee="0",
                    crypto_out_with_fee=str(executed),
                    fiat_out_no_fee=None,
                    fiat_fee=None,
                    notes=f"Binance Bot Sell (Strategy ID: {strategy_id})"
                )
                
                # InTransaction: received base currency (e.g. USDC)
                in_tx = InTransaction(
                    plugin="Binance_Bot",
                    unique_id=f"{order_no}_in",
                    raw_data=raw_data,
                    timestamp=timestamp_str,
                    asset=base_asset,
                    exchange="Binance",
                    holder=account_holder,
                    transaction_type="Buy",
                    spot_price="1.0",
                    crypto_in=str(trading_total),
                    crypto_fee="0",
                    fiat_in_no_fee=None,
                    fiat_in_with_fee=None,
                    fiat_fee=None,
                    notes=f"Binance Bot Sell Side-Effect (Strategy ID: {strategy_id})"
                )
                
                transactions.append(out_tx)
                transactions.append(in_tx)
                
        except Exception as e:
            logger.error("Error converting bot trade row to transaction: {}", str(e))
            continue
            
    logger.info("Successfully converted {} DaLI transactions from bot CSV.", len(transactions))
    return transactions
