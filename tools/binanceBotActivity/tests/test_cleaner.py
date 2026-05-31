import pytest
import pandas as pd
from tools.binanceBotActivity.binance_bot_activity.cleaner import clean_data

def test_clean_data_removes_canceled_and_duplicates():
    # Setup test data
    data = {
        "OrderNo": [1001, 1002, 1003, 1002, 1004, 1005],
        "Status": ["FILLED", "FILLED", "CANCELED", "FILLED", "cancelled", "NEW"],
        "Pair": ["SOLUSDC"] * 6
    }
    df = pd.DataFrame(data)
    
    cleaned = clean_data(df)
    
    # Assert CANCELED/cancelled and NEW are removed
    # 1003, 1004, and 1005 should be removed because of status
    # 1002 (second one) should be removed because of duplicate OrderNo
    # Resulting order nos should be: 1001, 1002
    assert len(cleaned) == 2
    assert list(cleaned["OrderNo"]) == [1001, 1002]

def test_clean_data_empty():
    df = pd.DataFrame()
    assert clean_data(df).empty
    assert clean_data(None).empty
