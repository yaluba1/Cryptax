import os
import argparse
import pandas as pd
from typing import List

from tools.binanceBotActivity.binance_bot_activity.parser import parse_amount_and_currency
from tools.binanceBotActivity.binance_bot_activity.cleaner import clean_data
from tools.binanceBotActivity.binance_bot_activity.exporter import generate_output_df, generate_pair_output_df, export_to_ods

def main(args_list: List[str] = None) -> int:
    """
    Main runner function for the Binance Bot Activity CLI tool.
    """
    parser = argparse.ArgumentParser(
        description="Reads Binance bot activity CSV data, cleans it, calculates bot metrics and P&L, and exports to ODS spreadsheet."
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to the input CSV file."
    )
    parser.add_argument(
        "--method", "-m",
        choices=["FIFO", "LIFO", "HIFO"],
        default="FIFO",
        help="Accounting method to use: FIFO, LIFO, or HIFO (default: FIFO)."
    )
    parser.add_argument(
        "--output", "-o",
        default="./out/",
        help="Path for the output file or directory (default: './out/')."
    )
    parser.add_argument(
        "--local-currency", "-lc",
        default="EUR",
        help="Local currency to convert base values to (default: EUR)."
    )
    parser.add_argument(
        "--language", "-l",
        default="EN",
        help="Language for report comments/explanation tab (e.g., EN, ES) (default: EN)."
    )
    parser.add_argument(
        "--country", "-c",
        default="ES",
        help="Country of the tax jurisdiction (e.g., ES, US) (default: ES)."
    )
    
    args = parser.parse_args(args_list)
    
    input_path = args.input
    method = args.method.upper()
    output_param = args.output
    local_currency = args.local_currency.upper()
    language = args.language.upper()
    country = args.country.upper()
    
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.")
        return 1
        
    print(f"Loading input file: {input_path}")
    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return 1
        
    # Clean data
    print("Cleaning data...")
    df_cleaned = clean_data(df)
    if df_cleaned.empty:
        print("Warning: Cleaned data is empty. No transactions to process.")
        return 0
        
    # Derive output file path
    input_filename = os.path.basename(input_path)
    name, _ = os.path.splitext(input_filename)
    out_filename = f"{name}_out.ods"
    
    # If output_param looks like a directory or ends with a slash, append the derived filename
    if output_param.endswith("/") or output_param.endswith("\\") or not os.path.splitext(output_param)[1]:
        output_file_path = os.path.join(output_param, out_filename)
    else:
        output_file_path = output_param
        
    output_dir = os.path.dirname(output_file_path) or "./out/"
    db_path = os.path.join(output_dir, "exchange_rates.db")
    
    # Initialize exchange rates DB
    from tools.binanceBotActivity.binance_bot_activity.rates import init_db, get_exchange_rate
    print(f"Initializing exchange rates cache database at: {db_path}")
    init_db(db_path)
    
    # Add parsed columns
    print("Parsing amounts and currencies...")
    df_cleaned["order_amount"] = df_cleaned["Order Amount"].apply(lambda x: parse_amount_and_currency(x)[0])
    df_cleaned["order_currency"] = df_cleaned["Order Amount"].apply(lambda x: parse_amount_and_currency(x)[1])
    df_cleaned["exec_amount"] = df_cleaned["Executed"].apply(lambda x: parse_amount_and_currency(x)[0])
    df_cleaned["total"] = df_cleaned["Trading total"].apply(lambda x: parse_amount_and_currency(x)[0])
    df_cleaned["base"] = df_cleaned["Trading total"].apply(lambda x: parse_amount_and_currency(x)[1])
    
    # Parse DateTime
    df_cleaned["parsed_time"] = pd.to_datetime(df_cleaned["Time"])
    
    # Fetch and apply exchange rates
    print(f"Applying exchange rates for local currency: {local_currency}...")
    
    def get_rate_row(row):
        base_curr = str(row["base"])
        dt = row["parsed_time"]
        return get_exchange_rate(db_path, base_curr, local_currency, dt)
        
    df_cleaned["exchange_rate"] = df_cleaned.apply(get_rate_row, axis=1)
    df_cleaned["total_local"] = df_cleaned["total"] * df_cleaned["exchange_rate"]
    
    # Generate output dataframe and operations list
    print(f"Calculating profit and loss using {method}...")
    df_output, df_ops = generate_output_df(df_cleaned, method, local_currency)
    df_output_pair, df_ops_pair = generate_pair_output_df(df_cleaned, method, local_currency)
    
    # Export to ODS
    print(f"Exporting summary to ODS: {output_file_path}")
    try:
        export_to_ods(df_output, df_ops, output_file_path, df_output_pair, df_ops_pair, language, country, method)
        print("Export completed successfully!")
    except Exception as e:
        print(f"Error exporting to ODS: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
