import sys
import os
from pathlib import Path

# Add project root to PYTHONPATH
sys.path.append(os.getcwd())

from worker.services.rp2_service import rp2_service
from worker.logging_config import logger
import pandas as pd

def repair_ods(ods_path):
    print(f"Repairing ODS file: {ods_path}...")
    xl = pd.ExcelFile(ods_path, engine='odf')
    new_sheets = {}
    
    cols_to_fix = ["Crypto In", "Fiat In No Fee", "Crypto Out No Fee", "Fiat Out No Fee", "Spot Price", "Crypto Sent", "Crypto Received"]
    
    for name in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=name)
        modified = False
        for col in cols_to_fix:
            if col in df.columns:
                def fix_val(x):
                    try:
                        # Convert to float to check if it's zero or negative
                        val = float(x)
                        if val <= 0:
                            return "0.0000000001"
                    except:
                        pass
                    return x
                
                df[col] = df[col].apply(fix_val)
                modified = True
        
        new_sheets[name] = df
    
    # Save the repaired ODS
    with pd.ExcelWriter(ods_path, engine='odf') as writer:
        for name, df in new_sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    print("ODS repair completed.")

def main():
    job_id = "638df5ca-d486-4854-bfed-abf0b12b0019"
    job_dir = Path("./data/jobs") / job_id
    
    if not job_dir.exists():
        print(f"Error: Job directory {job_dir} not found.")
        return

    print(f"Running RP2 manually for job {job_id} using existing ODS...")
    
    ods_file = job_dir / "crypto_data.ods"
    if ods_file.exists():
        repair_ods(ods_file)
    
    # In processor, country is job.country, but ES is the default
    country = "ES"
    
    # Input dir and output dir are usually the same for manual runs
    # but we can separate them if needed.
    input_dir = job_dir
    output_dir = job_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    success = rp2_service.run_rp2(
        country=country,
        input_dir=input_dir,
        output_dir=output_dir,
        prefix="" # prefix is empty in our current worker setup
    )
    
    if success:
        print(f"RP2 execution SUCCEEDED. Results in {output_dir}")
    else:
        print("RP2 execution FAILED. Check logs for details.")

if __name__ == "__main__":
    main()
