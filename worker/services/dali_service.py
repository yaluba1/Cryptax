"""
Service for executing the DaLI tool.
Generates the configuration file and runs the DaLI command.
"""

import subprocess
import shutil
from pathlib import Path
from worker.config import settings
from worker.logging_config import logger
import configparser

class DaliService:
    @staticmethod
    def generate_config(
        job_dir: Path,
        account_holder: str,
        exchange: str,
        api_key: str,
        api_secret: str,
        native_fiat: str
    ) -> Path:
        """
        Generates a DaLI .ini configuration file for the specific job.
        """
        config = configparser.ConfigParser()
        
        # Plugin section
        # For now we only support binance (dali.plugin.input.rest.binance_com)
        if exchange.lower() == 'binance':
            plugin_section = 'dali.plugin.input.rest.binance_com'
            config[plugin_section] = {
                'account_holder': account_holder,
                'api_key': api_key,
                'api_secret': api_secret,
                'native_fiat': native_fiat.upper()
            }
        else:
            raise ValueError(f"Exchange '{exchange}' not supported yet in DaLI service.")
            
        config_path = job_dir / "dali.ini"
        with open(config_path, 'w') as configfile:
            config.write(configfile)
            
        logger.debug("DaLI config generated at {}", config_path)
        return config_path

    @staticmethod
    def run_dali(country: str, config_path: Path, output_dir: Path) -> bool:
        """
        Executes the DaLI command (e.g., dali_es, dali_generic).
        """
        logger.info("Starting DaLI execution for country: {}", country)
        
        # Determine the binary based on country
        country_code = country.lower()
        if country_code == "generic":
            binary = "dali_generic"
        else:
            binary = f"dali_{country_code}"
            
        try:
            # Command: binary -o <output_dir> -s <config_path>
            # We use -s to read spot prices if missing
            cmd = [
                binary,
                "-o", str(output_dir),
                "-s",
                str(config_path)
            ]
            
            logger.debug("Executing command: {}", " ".join(cmd))
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False # We handle return code manually
            )
            
            if result.returncode != 0:
                logger.error("DaLI failed with exit code {}. Error: {}", result.returncode, result.stderr)
                return False
                
            # Verify output files exist
            ini_output = output_dir / "crypto_data.ini"
            ods_output = output_dir / "crypto_data.ods"
            
            if not ini_output.exists() or not ods_output.exists():
                logger.error("DaLI reported success but output files are missing. Output: {}", result.stdout)
                return False
                
            logger.info("DaLI execution completed successfully.")
            logger.debug("DaLI output: {}", result.stdout)
            DaliService._move_logs()
            return True
            
        except FileNotFoundError:
            logger.error("{} command not found. Ensure it is installed in the environment.", binary)
            return False
        except Exception as e:
            logger.error("An error occurred during DaLI execution: {}", str(e))
            DaliService._move_logs()
            return False

    @staticmethod
    def _move_logs():
        """
        Moves RP2/DaLI log files from the hardcoded ./log directory 
        to the project's preferred ./logs/rp2 directory.
        """
        src_dir = Path("./log")
        dest_dir = Path("./logs/rp2")
        
        if not src_dir.exists():
            return
            
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        for log_file in src_dir.glob("rp2_*.log"):
            try:
                shutil.move(str(log_file), str(dest_dir / log_file.name))
            except Exception as e:
                logger.warning("Failed to move log file {}: {}", log_file, str(e))

dali_service = DaliService()
