"""
Service for executing the DaLI tool.
Generates the configuration file and runs the dali-rp2 command.
"""

import subprocess
from pathlib import Path
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
        
        # General section
        config['general'] = {
            'account_holder': account_holder
        }
        
        # Plugin section
        # For now we only support binance (dali.plugin.input.rest.binance_com)
        if exchange.lower() == 'binance':
            plugin_section = 'dali.plugin.input.rest.binance_com'
            config[plugin_section] = {
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
    def run_dali(config_path: Path, output_dir: Path) -> bool:
        """
        Executes the dali-rp2 command.
        """
        logger.info("Starting DaLI execution...")
        
        try:
            # Command: dali-rp2 -o <output_dir> <config_path>
            # We use -s to read spot prices if missing
            cmd = [
                "dali-rp2",
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
                
            logger.info("DaLI execution completed successfully.")
            logger.debug("DaLI output: {}", result.stdout)
            return True
            
        except FileNotFoundError:
            logger.error("dali-rp2 command not found. Ensure it is installed in the environment.")
            return False
        except Exception as e:
            logger.error("An error occurred during DaLI execution: {}", str(e))
            return False

dali_service = DaliService()
