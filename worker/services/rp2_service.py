"""
Service for executing the RP2 tool.
Supports country-specific RP2 plugins like rp2_es.
"""

import subprocess
from pathlib import Path
from worker.logging_config import logger

class Rp2Service:
    @staticmethod
    def run_rp2(country: str, input_dir: Path, output_dir: Path, prefix: str = "") -> bool:
        """
        Executes the RP2 tool for the specified country.
        Currently only supports 'ES' (Spain).
        """
        logger.info("Starting RP2 execution for country: {}", country)
        
        # Determine the binary based on country
        if country.upper() == "ES":
            binary = "rp2_es"
        elif country.upper() == "GENERIC":
            binary = "rp2"
        else:
            logger.error("Country '{}' not supported yet in RP2 service.", country)
            return False
            
        # Build file paths
        prefix_str = f"{prefix}_" if prefix else ""
        ini_file = input_dir / f"{prefix_str}crypto_data.ini"
        ods_file = input_dir / f"{prefix_str}crypto_data.ods"
        
        # Verify input files exist
        if not ini_file.exists():
            logger.error("RP2 input INI file not found: {}", ini_file)
            return False
        if not ods_file.exists():
            logger.error("RP2 input ODS file not found: {}", ods_file)
            return False
            
        try:
            # Command: binary -o <output_dir> -p <prefix> <ini_file> <ods_file>
            cmd = [
                binary,
                "-o", str(output_dir),
            ]
            if prefix:
                cmd.extend(["-p", prefix])
            
            cmd.extend([str(ini_file), str(ods_file)])
            
            logger.debug("Executing command: {}", " ".join(cmd))
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                logger.error("RP2 failed with exit code {}. Error: {}", result.returncode, result.stderr)
                return False
                
            logger.info("RP2 execution completed successfully.")
            logger.debug("RP2 output: {}", result.stdout)
            return True
            
        except FileNotFoundError:
            logger.error("{} command not found. Ensure it is installed in the environment.", binary)
            return False
        except Exception as e:
            logger.error("An error occurred during RP2 execution: {}", str(e))
            return False

rp2_service = Rp2Service()
