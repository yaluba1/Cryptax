# Binance Bot Activity CLI Tool

A robust and precise Python command-line utility for cleaning, parsing, and calculating the financial performance of Binance trading bots. It reads transaction activity data from an input CSV file, groups transactions by Strategy ID, applies FIFO, LIFO, or HIFO crypto tax matching algorithms to compute Profit and Loss (P&L), retrieves and caches historical exchange rates for tax declarations, and outputs a beautifully formatted, multi-sheet Excel summary and audit report.

## Key Features

- **Transaction Data Cleaning**:
  - Automatically filters out inactive rows with status `CANCELED` (case-insensitively).
  - Deduplicates transaction entries by removing redundant rows based on `OrderNo` (keeping the first occurrence).
- **Exact Numeric Parsing**: Extricates numerical quantities and currency codes safely from compound text values (e.g., `0.1990000000SOL` -> `0.199` and `SOL`).
- **Local Currency Conversion & Compliance**:
  - Supports automatic conversion of base currency (e.g. USDC) to a local currency (default **`EUR`**) for tax declarations.
  - For **EUR**, integrates with the **Frankfurter API** to retrieve official **European Central Bank (ECB)** daily reference rates.
  - For other currencies, integrates with the public **Binance Klines API** to retrieve minute-by-minute historical candle rates.
- **SQLite Rate Caching**:
  - Creates a local SQLite database (`exchange_rates.db`) in your output directory.
  - Persistently caches all retrieved rates, minimizing API network calls and preventing rate-limiting on large datasets.
- **Flexible Accounting Systems**: Offers 3 industry-standard matching methodologies:
  - **FIFO (First-In, First-Out)**: Disposes of the oldest purchased inventory first.
  - **LIFO (Last-In, First-Out)**: Disposes of the most recently purchased inventory first.
  - **HIFO (Highest-In, First-Out)**: Disposes of the highest cost-basis inventory first (great for tax-minimization).
- **Premium Multi-Sheet Excel Export**:
  - **Sheet 1 (`Bot Activity Summary`)**: High-level bot summary including realized P&L in base and local currency.
  - **Sheet 2 (`Closed Operations`)**: Detailed granular trace of every closed trade (Buy OrderNo matched to Sell OrderNo, amounts in base/pair, buy/sell exchange rates, and P&L in base/local).
  - Segoe UI styling with navy blue headers, light-grey zebra row highlighting, auto-adjusted column widths, and bold green/red P&L color-coding.

---

## Installation & Setup

All tool execution is managed seamlessly via **`uv`**, the lightning-fast Python package manager.

Ensure you have `uv` installed, then synchronize dependencies by running from the project root:

```bash
uv sync
```

---

## Usage Guide

The tool can be executed as a module from the root directory of the `CrypTax` repository.

### Pre-requisites

Retrieve from your Binance account the bot activity data for the period you want to analyze as a csv file and save it to a file. It will have all the columns described in the next section.

Binance limits the maximum lenght of a period to 6 months. If you need to analyze a longer period, you should retrieve the data in multiple files, one for each 6-month period, and join them together in a single csv file manually.

Since I use this tool for tax declaration purposes, I retrieve data for the whole fiscal year (which is Spain corresponds to a natural year) and I join the two 6-month reports into a single csv that I then use for the tax calculation.

Note that Binance does **NOT** include the comissions in the bot activity. You need to retrieve the invoices for the commissions separately. In my account, Binance provides this in a monthly basis and in pdf format only.

### Run CLI

```bash
uv run python -m tools.binanceBotActivity.binance_bot_activity --input <path_to_csv> [--method <FIFO|LIFO|HIFO>] [--local-currency <CURR>] [--output <output_path>]
```

### Argument Reference

| Option             | Shorthand | Required | Default  | Description                                                                                                                               |
| :----------------- | :-------- | :------- | :------- | :---------------------------------------------------------------------------------------------------------------------------------------- |
| `--input`          | `-i`      | **Yes**  | _None_   | Absolute or relative path to the input Binance bot CSV file.                                                                              |
| `--method`         | `-m`      | No       | `FIFO`   | Accounting method to use. Must be one of `FIFO`, `LIFO`, or `HIFO`.                                                                       |
| `--local-currency` | `-lc`     | No       | `EUR`    | Local currency to convert base values to for tax compliance (e.g. EUR, GBP, USD).                                                         |
| `--output`         | `-o`      | No       | `./out/` | Path for the output file or directory. If a directory is specified, a filename is derived from the input file as `<input_name>_out.xlsx`. |

### Example Executions

- **Using LIFO with EUR Conversion (default)**:

  ```bash
  uv run python -m tools.binanceBotActivity.binance_bot_activity --input tools/binanceBotActivity/data/BinanceBot_2025.csv --method LIFO
  ```

  _Generates: `./out/BinanceBot_2025_out.xlsx` and caches exchange rates to `./out/exchange_rates.db`_

- **Converting to a different local currency (e.g., GBP)**:
  ```bash
  uv run python -m tools.binanceBotActivity.binance_bot_activity -i tools/binanceBotActivity/data/BinanceBot_2025.csv -m FIFO -lc GBP
  ```

---

## Running the Test Suite

We follow strict test-driven development (TDD) methodologies. The test suite covers all components including value parsers, cleaner functions, accounting matchers, exchange rate fetchers & database caches, and spreadsheet exporters.

To run the tests, execute from the repository root:

```bash
$env:PYTHONPATH="c:\Users\jnoguera\Documents\repos\CrypTax"; uv run python -m pytest tools/binanceBotActivity/tests -v
```

### Running with Test Coverage Report

To generate the full code coverage report in the terminal:

```bash
$env:PYTHONPATH="c:\Users\jnoguera\Documents\repos\CrypTax"; uv run python -m pytest tools/binanceBotActivity/tests --cov=tools.binanceBotActivity.binance_bot_activity --cov-report=term-missing
```

---

## Output Excel Format

The exported Excel workbook contains two sheets:

### Sheet 1: `Bot Activity Summary`

Provides the summarized trading performance of each bot strategy.

| Column Name       | Type    | Display Format   | Description                                                  |
| :---------------- | :------ | :--------------- | :----------------------------------------------------------- |
| `bot_id`          | String  | Plain Text (`@`) | The unique `Strategy_Id` representing the bot.               |
| `pair`            | String  | Plain Text       | The trading pair (e.g. `SOLUSDC`).                           |
| `base`            | String  | Plain Text       | The base currency (e.g. `USDC`).                             |
| `local`           | String  | Plain Text       | The target local currency (e.g. `EUR`).                      |
| `count_buy`       | Integer | `#,##0`          | Number of executed buy trades.                               |
| `count_sell`      | Integer | `#,##0`          | Number of executed sell trades.                              |
| `pair_vol_buy`    | Float   | `#,##0.0000`     | Total volume bought of the traded asset.                     |
| `pair_vol_sell`   | Float   | `#,##0.0000`     | Total volume sold of the traded asset.                       |
| `rem_pair_amount` | Float   | `#,##0.0000`     | The remaining amount of the traded asset left in the wallet. |
| `base_vol_buy`    | Float   | `#,##0.0000`     | Total volume bought in base currency.                        |
| `base_vol_sell`   | Float   | `#,##0.0000`     | Total volume sold in base currency.                          |
| `pl`              | Float   | `#,##0.00`       | Realized Profit and Loss in base currency (color-styled).    |
| `pl_local`        | Float   | `#,##0.00`       | Realized Profit and Loss in local currency (color-styled).   |

### Sheet 2: `Closed Operations`

Provides a detailed audit trail of every closed transaction (matched buy-sell pair).

| Column Name          | Type   | Display Format | Description                                                      |
| :------------------- | :----- | :------------- | :--------------------------------------------------------------- |
| `bot_id`             | String | Plain Text     | The unique Strategy ID.                                          |
| `pair`               | String | Plain Text     | The trading pair (e.g., `SOLUSDC`).                              |
| `base`               | String | Plain Text     | The base currency.                                               |
| `local`              | String | Plain Text     | The target local currency.                                       |
| `Time`               | String | Plain Text     | Execution date and time of the closing (sell) order.             |
| `buy_OrderNo`        | String | Plain Text     | The unique ID of the matching buy transaction.                   |
| `sell_OrderNo`       | String | Plain Text     | The unique ID of the matching sell transaction.                  |
| `pair_amount`        | Float  | `#,##0.0000`   | Proportional matched amount in pair currency (e.g., SOL).        |
| `base_buy_amount`    | Float  | `#,##0.0000`   | Proportional cost basis in base currency.                        |
| `base_sell_amount`   | Float  | `#,##0.0000`   | Proportional proceeds in base currency.                          |
| `pl_base`            | Float  | `#,##0.00`     | Realized gain or loss on this match in base currency.            |
| `pl_local`           | Float  | `#,##0.00`     | Realized gain or loss on this match in local currency.           |
| `buy_exchange_rate`  | Float  | `#,##0.0000`   | Base-to-local currency exchange rate on the BUY execution date.  |
| `sell_exchange_rate` | Float  | `#,##0.0000`   | Base-to-local currency exchange rate on the SELL execution date. |
