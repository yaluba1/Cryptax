import time
import ezodf
from pathlib import Path
from datetime import datetime
import ccxt
from worker.logging_config import logger
from worker.services.dali_service import dali_service

class PriceEnricher:
    @staticmethod
    def get_year_end_price(asset: str, fiat: str, tax_year: int, exchange_name: str = 'binance') -> float:
        """
        Fetches the year-end closing price of an asset in the given fiat currency
        on December 31st of the tax_year at 23:00:00 UTC using CCXT.
        """
        asset = asset.upper()
        fiat = fiat.upper()
        exchange_name = exchange_name.lower()

        # Handle simple stablecoin and fiat cases
        if asset == fiat:
            return 1.0
        if asset in ['USDT', 'USDC', 'BUSD'] and fiat in ['USD']:
            return 1.0
        if asset in ['EUR', 'ZEUR'] and fiat in ['EUR']:
            return 1.0

        # December 31st at 23:00:00 UTC
        dt_str = f"{tax_year}-12-31 23:00:00"
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            ts_ms = int(dt.timestamp() * 1000)
        except Exception as e:
            logger.error("Failed to parse year-end date string: {}", e)
            return None

        # Check Redis price cache first
        cached = dali_service._get_cached_price(exchange_name, asset, ts_ms)
        if cached is not None:
            logger.info("Found cached year-end price for {}/{}: {}", asset, fiat, cached)
            return float(cached)

        # Initialize CCXT exchange client
        if exchange_name == 'kraken':
            exchange = ccxt.kraken({'enableRateLimit': True})
            request_delay = 1.5
        else:
            exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})
            request_delay = 0.5

        def fetch_safe(symbol):
            time.sleep(request_delay)
            for attempt in range(3):
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', since=ts_ms, limit=1)
                    if ohlcv and len(ohlcv) > 0:
                        return float(ohlcv[0][4])  # Return close price
                    return None
                except ccxt.RateLimitExceeded:
                    time.sleep((attempt + 1) * 3)
                except Exception as ex:
                    logger.debug("Failed to fetch price for symbol {}: {}", symbol, ex)
                    break
            return None

        price = None

        # Strategy 1: Direct pair (e.g., SOL/EUR or BNB/EUR)
        symbol = f"{asset}/{fiat}"
        price = fetch_safe(symbol)

        # Strategy 2: Inverted pair (e.g., EUR/BTC -> 1 / price)
        if price is None:
            inv_symbol = f"{fiat}/{asset}"
            inv_price = fetch_safe(inv_symbol)
            if inv_price:
                price = 1.0 / inv_price

        # Strategy 3: Stablecoin / Bridge pair (e.g. SOL/USDT then USDT/EUR)
        if price is None and asset != 'USDT':
            asset_usdt_price = fetch_safe(f"{asset}/USDT")
            usdt_fiat_price = fetch_safe(f"USDT/{fiat}")
            if not usdt_fiat_price:
                fiat_usdt_price = fetch_safe(f"{fiat}/USDT")
                if fiat_usdt_price:
                    usdt_fiat_price = 1.0 / fiat_usdt_price
            if asset_usdt_price and usdt_fiat_price:
                price = asset_usdt_price * usdt_fiat_price

        # Strategy 4: Bridge pair via BTC
        if price is None and asset != 'BTC':
            asset_btc_price = fetch_safe(f"{asset}/BTC")
            btc_fiat_price = fetch_safe(f"BTC/{fiat}")
            if asset_btc_price and btc_fiat_price:
                price = asset_btc_price * btc_fiat_price

        if price is not None:
            logger.info("Retrieved year-end price for {}/{}: {}", asset, fiat, price)
            dali_service._save_cached_price(exchange_name, asset, ts_ms, price)
            return price

        logger.warning("Could not automatically retrieve year-end price for {}/{}", asset, fiat)
        return None

    @classmethod
    def enrich_open_positions_report(cls, ods_path: Path, fiat: str, tax_year: int, exchange_name: str) -> bool:
        """
        Reads the open positions ODS file, identifies 'Enter asset value' cells,
        fetches their correct year-end closing price, and saves them back to the ODS.
        """
        if not ods_path.exists():
            logger.error("Open positions ODS report not found: {}", ods_path)
            return False

        logger.info("Starting automatic price enrichment for: {}", ods_path.name)
        try:
            doc = ezodf.opendoc(str(ods_path))
            sheet_names = [s.name for s in doc.sheets]
            if 'Entrada' not in sheet_names:
                logger.error("Tab 'Entrada' not found in open positions ODS report. Found: {}", sheet_names)
                return False

            sheet = doc.sheets['Entrada']
            modified = False

            # The Entrada sheet structure:
            # Row 2: ['Activo', 'Precio', None]
            # Row 3+: [Asset, 'Enter asset value', None]
            for r in range(3, sheet.nrows()):
                asset_cell = sheet[r, 0]
                price_cell = sheet[r, 1]

                asset_name = asset_cell.value
                price_value = price_cell.value

                if asset_name and price_value == 'Enter asset value':
                    # Attempt to fetch the year-end closing price
                    price = cls.get_year_end_price(
                        asset=asset_name,
                        fiat=fiat,
                        tax_year=tax_year,
                        exchange_name=exchange_name
                    )

                    if price is not None:
                        # Write the fetched price back to the cell as a float
                        price_cell.set_value(price)
                        modified = True
                        logger.info("Enriched open position {} with price: {}", asset_name, price)
                    else:
                        logger.warning("Skipped enriching open position {} due to missing price", asset_name)

            if modified:
                doc.save()
                logger.info("Successfully saved enriched ODS report: {}", ods_path.name)
            else:
                logger.info("No 'Enter asset value' placeholders needed enrichment in {}", ods_path.name)
            return True

        except Exception as e:
            logger.error("Failed to enrich open positions ODS: {}", e)
            logger.exception(e)
            return False

price_enricher = PriceEnricher()
