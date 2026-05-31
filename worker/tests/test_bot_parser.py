import pytest
from pathlib import Path
from worker.services.bot_parser_service import parse_bot_csv_to_dali_transactions
from dali.in_transaction import InTransaction
from dali.out_transaction import OutTransaction

def test_parse_bot_csv_to_dali_transactions(tmp_path):
    # 1. Create a dummy bot CSV file
    csv_content = (
        "Strategy_Id,Pair,Side,Time,OrderNo,Order Amount,Executed,Trading total,Status\n"
        "12345,SOLUSDC,BUY,2025-01-01 10:20:30,ORD001,0.199SOL,0.199SOL,20.123USDC,FILLED\n"
        "12345,SOLUSDC,SELL,2025-01-02 11:30:45,ORD002,0.199SOL,0.199SOL,22.456USDC,FILLED\n"
    )
    csv_file = tmp_path / "bot_activity_test.csv"
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write(csv_content)
        
    # 2. Run the parser service
    transactions = parse_bot_csv_to_dali_transactions(csv_file, "test@example.com")
    
    # 3. Assertions
    assert len(transactions) == 4  # 2 rows * 2 double-entry transactions = 4
    
    # Check BUY transactions
    buy_in = [tx for tx in transactions if tx.unique_id == "ORD001_in"][0]
    buy_out = [tx for tx in transactions if tx.unique_id == "ORD001_out"][0]
    
    assert isinstance(buy_in, InTransaction)
    assert buy_in.asset == "SOL"
    assert buy_in.crypto_in == "0.199"
    assert float(buy_in.spot_price) == pytest.approx(20.123 / 0.199)
    assert "Strategy ID: 12345" in buy_in.notes
    
    assert isinstance(buy_out, OutTransaction)
    assert buy_out.asset == "USDC"
    assert buy_out.crypto_out_no_fee == "20.123"
    assert buy_out.spot_price == "1.0"
    
    # Check SELL transactions
    sell_out = [tx for tx in transactions if tx.unique_id == "ORD002_out"][0]
    sell_in = [tx for tx in transactions if tx.unique_id == "ORD002_in"][0]
    
    assert isinstance(sell_out, OutTransaction)
    assert sell_out.asset == "SOL"
    assert sell_out.crypto_out_no_fee == "0.199"
    assert float(sell_out.spot_price) == pytest.approx(22.456 / 0.199)
    
    assert isinstance(sell_in, InTransaction)
    assert sell_in.asset == "USDC"
    assert sell_in.crypto_in == "22.456"
    assert sell_in.spot_price == "1.0"
