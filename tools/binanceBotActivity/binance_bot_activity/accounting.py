import pandas as pd
from typing import List, Dict, Any, Tuple

def calculate_bot_pl(bot_df: pd.DataFrame, method: str) -> float:
    """
    Calculates the profit and loss (P&L) for a single bot using the specified
    accounting method: FIFO, LIFO, or HIFO.
    
    Backward compatible wrapper that returns only the base currency P&L float.
    """
    pl, _, _ = calculate_bot_pl_detailed(bot_df, method)
    return pl

def calculate_bot_pl_detailed(bot_df: pd.DataFrame, method: str) -> Tuple[float, float, List[Dict[str, Any]]]:
    """
    Calculates P&L in both base currency and local currency, and returns the detailed
    closed operations list.
    
    The dataframe 'bot_df' must contain cleaned transactions for the bot,
    sorted chronologically.
    
    Optional/Calculated columns:
    - total_local: float (amount in local currency)
    - exchange_rate: float (base to local rate)
    """
    if bot_df.empty:
        return 0.0, 0.0, []
        
    # Sort chronologically by execution time, then OrderNo for deterministic ordering
    sorted_df = bot_df.sort_values(by=["parsed_time", "OrderNo"], ascending=[True, True])
    
    pl = 0.0
    pl_local = 0.0
    closed_ops: List[Dict[str, Any]] = []
    buys: List[Dict[str, Any]] = []
    
    # Check if local currency columns exist, otherwise fallback to base currency values
    has_local = "total_local" in sorted_df.columns
    
    for _, row in sorted_df.iterrows():
        side = str(row["Side"]).upper().strip()
        qty = float(row["order_amount"])
        total_val = float(row["total"])
        time_val = row["parsed_time"]
        order_no = row["OrderNo"]
        
        total_val_local = float(row["total_local"]) if has_local else total_val
        rate_val = float(row["exchange_rate"]) if "exchange_rate" in sorted_df.columns else 1.0
        
        # Calculate unit price for this transaction
        price = total_val / qty if qty > 0.0 else 0.0
        price_local = total_val_local / qty if qty > 0.0 else 0.0
        
        if side == "BUY":
            buys.append({
                "qty": qty,
                "price": price,
                "price_local": price_local,
                "time": time_val,
                "order_no": order_no,
                "exchange_rate": rate_val,
                "total": total_val,
                "total_local": total_val_local
            })
        elif side == "SELL":
            sell_qty = qty
            sell_price = price
            sell_price_local = price_local
            
            while sell_qty > 1e-9:  # Avoid float precision issues
                # Filter to only get BUYs that occurred on or before this SELL and have remaining qty
                available_buys = [b for b in buys if b["qty"] > 1e-9 and b["time"] <= time_val]
                
                if not available_buys:
                    # If we sold more than we have in inventory, treat the excess cost basis as 0
                    excess_pl = sell_qty * sell_price
                    excess_pl_local = sell_qty * sell_price_local
                    pl += excess_pl
                    pl_local += excess_pl_local
                    
                    closed_ops.append({
                        "Time": time_val.strftime("%Y-%m-%d %H:%M:%S") if isinstance(time_val, pd.Timestamp) else str(time_val),
                        "buy_OrderNo": "UNMATCHED",
                        "sell_OrderNo": str(order_no),
                        "pair_amount": sell_qty,
                        "base_buy_amount": 0.0,
                        "base_sell_amount": sell_qty * sell_price,
                        "pl_base": excess_pl,
                        "pl_local": excess_pl_local,
                        "buy_exchange_rate": 1.0,
                        "sell_exchange_rate": rate_val
                    })
                    sell_qty = 0.0
                    break
                
                # Sort available buys depending on accounting method
                if method == "FIFO":
                    # Earliest buys first (chronological)
                    available_buys.sort(key=lambda x: (x["time"], x["order_no"]))
                elif method == "LIFO":
                    # Latest buys first (reverse chronological)
                    available_buys.sort(key=lambda x: (x["time"], x["order_no"]), reverse=True)
                elif method == "HIFO":
                    # Highest unit price first. Tie-breakers: earliest first, then lowest OrderNo first.
                    available_buys.sort(key=lambda x: (-x["price"], x["time"], x["order_no"]))
                else:
                    raise ValueError(f"Unknown accounting method: {method}")
                
                selected_buy = available_buys[0]
                matched_qty = min(sell_qty, selected_buy["qty"])
                
                # Proportional totals for the matched part
                buy_fraction = matched_qty / selected_buy["qty"] if selected_buy["qty"] > 0 else 0.0
                
                # Profit/Loss for this match
                trade_pl = matched_qty * (sell_price - selected_buy["price"])
                trade_pl_local = matched_qty * (sell_price_local - selected_buy["price_local"])
                
                pl += trade_pl
                pl_local += trade_pl_local
                
                closed_ops.append({
                    "Time": time_val.strftime("%Y-%m-%d %H:%M:%S") if isinstance(time_val, pd.Timestamp) else str(time_val),
                    "buy_OrderNo": str(selected_buy["order_no"]),
                    "sell_OrderNo": str(order_no),
                    "pair_amount": matched_qty,
                    "base_buy_amount": matched_qty * selected_buy["price"],
                    "base_sell_amount": matched_qty * sell_price,
                    "pl_base": trade_pl,
                    "pl_local": trade_pl_local,
                    "buy_exchange_rate": selected_buy["exchange_rate"],
                    "sell_exchange_rate": rate_val
                })
                
                # Deduct matched quantity from both
                sell_qty -= matched_qty
                selected_buy["qty"] -= matched_qty
                
    return pl, pl_local, closed_ops

