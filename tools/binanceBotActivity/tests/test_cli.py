import pytest
import os
import pandas as pd
from tools.binanceBotActivity.binance_bot_activity.__main__ import main

def test_cli_missing_input():
    with pytest.raises(SystemExit):
        main([])

def test_cli_non_existent_input():
    res = main(["--input", "non_existent_file.csv"])
    assert res == 1

def test_cli_success(tmp_path):
    # Create a small mock CSV file
    csv_file = os.path.join(tmp_path, "BinanceBot_test.csv")
    data = {
        "Date(UTC)": ["11/13/2025 17:15", "11/13/2025 17:14"],
        "OrderNo": [2945850893, 2945840875],
        "Pair": ["SOLUSDC", "SOLUSDC"],
        "Type": ["Limit", "Limit"],
        "Side": ["BUY", "SELL"],
        "Strategy_Id": [8483584, 8483584],
        "Order Price": [150.0, 150.84],
        "Order Amount": ["0.2000000000SOL", "0.1990000000SOL"],
        "Time": ["11/13/2025 17:19", "11/13/2025 17:15"],
        "Executed": ["0.2000000000SOL", "0.1990000000SOL"],
        "Average Price": [150.0, 150.84],
        "Trading total": ["30.0000000000USDC", "30.0171600000USDC"],
        "Status": ["FILLED", "FILLED"]
    }
    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False)
    
    output_dir = os.path.join(tmp_path, "out")
    
    # Run CLI main runner
    res = main(["--input", csv_file, "--method", "FIFO", "--output", output_dir])
    
    assert res == 0
    # Expected output file: BinanceBot_test_out.ods under output_dir
    expected_output_file = os.path.join(output_dir, "BinanceBot_test_out.ods")
    assert os.path.exists(expected_output_file)
