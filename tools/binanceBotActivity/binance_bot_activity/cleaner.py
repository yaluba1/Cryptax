import pandas as pd

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans the Binance bot activity data:
    1. Removes rows with status 'CANCELED' or 'CANCELLED' (case-insensitive).
    2. Removes rows that have duplicate 'OrderNo' values (keeps the first occurrence).
    """
    if df is None or df.empty:
        return pd.DataFrame()
        
    df_cleaned = df.copy()
    
    # Remove rows with status "CANCELED", "CANCELLED", or "NEW" (case-insensitive)
    if "Status" in df_cleaned.columns:
        status_upper = df_cleaned["Status"].astype(str).str.upper().str.strip()
        mask = ~status_upper.isin(["CANCELED", "CANCELLED", "NEW"])
        df_cleaned = df_cleaned[mask]
        
    # Remove duplicate OrderNo (keep first occurrence)
    if "OrderNo" in df_cleaned.columns:
        df_cleaned = df_cleaned.drop_duplicates(subset=["OrderNo"], keep="first")
        
    return df_cleaned
