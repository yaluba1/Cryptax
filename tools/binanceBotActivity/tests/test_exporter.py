import pytest
import pandas as pd
import openpyxl
import os
from datetime import datetime
from tools.binanceBotActivity.binance_bot_activity.exporter import generate_output_df, export_to_ods

def test_generate_output_df():
    # Setup cleaned dataframe with exchange_rate and total_local columns
    data = {
        "Strategy_Id": [8483584, 8483584, 7165901, 7165901],
        "Pair": ["SOLUSDC", "SOLUSDC", "BNBUSDC", "BNBUSDC"],
        "Side": ["BUY", "SELL", "BUY", "SELL"],
        "order_amount": [2.0, 1.5, 0.5, 0.5],
        "total": [300.0, 240.0, 100.0, 110.0],
        "parsed_time": [
            datetime(2025, 1, 1, 10, 0, 0),
            datetime(2025, 1, 1, 11, 0, 0),
            datetime(2025, 1, 1, 10, 0, 0),
            datetime(2025, 1, 1, 11, 0, 0)
        ],
        "base": ["USDC", "USDC", "USDC", "USDC"],
        "OrderNo": [1, 2, 3, 4],
        "exchange_rate": [0.90, 0.92, 0.90, 0.92],
        "total_local": [270.0, 220.8, 90.0, 101.2]
    }
    df = pd.DataFrame(data)
    
    out_df, ops_df = generate_output_df(df, "FIFO", "EUR")
    
    assert len(out_df) == 2
    # Sorted by bot_id ascending (which is string, so "7165901" comes before "8483584")
    row_716 = out_df.iloc[0]
    row_848 = out_df.iloc[1]
    
    assert row_716["bot_id"] == "7165901"
    assert row_716["pair"] == "BNBUSDC"
    assert row_716["base"] == "USDC"
    assert row_716["local"] == "EUR"
    assert row_716["count_buy"] == 1
    assert row_716["count_sell"] == 1
    assert row_716["pair_vol_buy"] == 0.5
    assert row_716["pair_vol_sell"] == 0.5
    assert row_716["rem_pair_amount"] == 0.0
    assert row_716["base_vol_buy"] == 100.0
    assert row_716["base_vol_sell"] == 110.0
    # PL = 0.5 * (220 - 200) = 10.0
    assert abs(row_716["pl"] - 10.0) < 1e-9
    # PL Local = 0.5 * (202.4 - 180) = 11.2
    assert abs(row_716["pl_local"] - 11.2) < 1e-9
    
    assert row_848["bot_id"] == "8483584"
    assert row_848["pair"] == "SOLUSDC"
    assert row_848["count_buy"] == 1
    assert row_848["count_sell"] == 1
    assert row_848["pair_vol_buy"] == 2.0
    assert row_848["pair_vol_sell"] == 1.5
    assert row_848["rem_pair_amount"] == 0.5
    # 1.5 sold at price 160 (total 240). Buy price was 150 (total 300 for 2.0).
    # PL = 1.5 * (160 - 150) = 15.0
    assert abs(row_848["pl"] - 15.0) < 1e-9
    # PL Local: Sell price local = 220.8/1.5 = 147.2. Buy price local = 270.0/2.0 = 135.0.
    # PL Local = 1.5 * (147.2 - 135.0) = 18.3
    assert abs(row_848["pl_local"] - 18.3) < 1e-9

def test_export_to_ods(tmp_path):
    output_file = os.path.join(tmp_path, "test_out.ods")
    
    # Create mock output summary dataframe
    data = {
        "bot_id": ["7165901", "8483584"],
        "pair": ["BNBUSDC", "SOLUSDC"],
        "base": ["USDC", "USDC"],
        "local": ["EUR", "EUR"],
        "count_buy": [1, 2],
        "count_sell": [1, 3],
        "pair_vol_buy": [0.5000, 2.3456],
        "pair_vol_sell": [0.5000, 2.1111],
        "rem_pair_amount": [0.0000, 0.2345],
        "base_vol_buy": [100.0000, 350.2345],
        "base_vol_sell": [110.0000, 310.5555],
        "pl": [10.00, -5.50],
        "pl_local": [9.20, -5.06]
    }
    df = pd.DataFrame(data)
    
    # Create mock operations dataframe
    ops_data = {
        "bot_id": ["7165901", "8483584"],
        "pair": ["BNBUSDC", "SOLUSDC"],
        "base": ["USDC", "USDC"],
        "local": ["EUR", "EUR"],
        "Time": ["2025-01-01 11:00:00", "2025-01-01 12:00:00"],
        "buy_OrderNo": ["3", "1"],
        "sell_OrderNo": ["4", "2"],
        "pair_amount": [0.5000, 1.5000],
        "base_buy_amount": [100.0000, 225.0000],
        "base_sell_amount": [110.0000, 240.0000],
        "pl_base": [10.00, 15.00],
        "pl_local": [9.20, 13.80],
        "buy_exchange_rate": [0.9000, 0.9000],
        "sell_exchange_rate": [0.9200, 0.9200]
    }
    df_ops = pd.DataFrame(ops_data)
    
    export_to_ods(df, df_ops, output_file)
    
    assert os.path.exists(output_file)
    
    # Load and verify ODS
    df1 = pd.read_excel(output_file, engine="odf", sheet_name="Bot Activity Summary")
    df2 = pd.read_excel(output_file, engine="odf", sheet_name="Closed Operations")
    
    # Verification
    assert list(df1.columns) == [
        "bot_id", "pair", "base", "local", "count_buy", "count_sell",
        "pair_vol_buy", "pair_vol_sell", "rem_pair_amount", "base_vol_buy", "base_vol_sell", "pl", "pl_local"
    ]
    
    assert str(df1.iloc[0]["bot_id"]) == "7165901"
    assert float(df1.iloc[0]["pl_local"]) == 9.20
    
    assert list(df2.columns) == [
        "bot_id", "pair", "base", "local", "Time", "buy_OrderNo", "sell_OrderNo",
        "pair_amount", "base_buy_amount", "base_sell_amount", "pl_base", "pl_local",
        "buy_exchange_rate", "sell_exchange_rate"
    ]
    
    assert str(df2.iloc[0]["Time"]) == "2025-01-01 11:00:00"
    assert str(df2.iloc[0]["buy_OrderNo"]) == "3"
    assert float(df2.iloc[0]["pair_amount"]) == 0.5
    assert float(df2.iloc[0]["pl_local"]) == 9.20
    assert float(df2.iloc[0]["buy_exchange_rate"]) == 0.9000
