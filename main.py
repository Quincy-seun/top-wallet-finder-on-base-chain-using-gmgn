#!/usr/bin/env python3
"""
Master Script to run Basecoins.py, Base.py, and refined.py sequentially.
Run this script to execute all three scripts one after another.
"""

import subprocess
import sys
import os
from datetime import datetime

def run_script(script_name, script_path=None):
    """
    Run a Python script and wait for it to complete.
    
    Args:
        script_name (str): Name of the script (for display purposes)
        script_path (str): Path to the script file (if None, uses script_name)
    
    Returns:
        bool: True if script ran successfully, False otherwise
    """
    if script_path is None:
        script_path = script_name
    
    print("\n" + "="*80)
    print(f"  STARTING: {script_name}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    try:
        # Run the script and wait for completion
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=False,  # Let output print to console in real-time
            text=True
        )
        
        if result.returncode == 0:
            print("\n" + "="*80)
            print(f"  ✓ COMPLETED: {script_name} (Success)")
            print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*80 + "\n")
            return True
        else:
            print("\n" + "="*80)
            print(f"  ✗ FAILED: {script_name} (Exit code: {result.returncode})")
            print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*80 + "\n")
            return False
            
    except FileNotFoundError:
        print(f"\n[ERROR] Script not found: {script_path}")
        print(f"Make sure {script_path} exists in the current directory.\n")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error running {script_name}: {e}\n")
        return False

def check_required_files():
    """Check if all required script files exist."""
    required_scripts = ["Basecoins.py", "Base.py", "refined.py"]
    missing = []
    
    for script in required_scripts:
        if not os.path.exists(script):
            missing.append(script)
    
    if missing:
        print("\n" + "="*80)
        print("ERROR: Missing required script files:")
        for script in missing:
            print(f"  - {script}")
        print("\nMake sure all three scripts are in the same directory as this master script.")
        print("="*80 + "\n")
        return False
    return True

def main():
    """Main function to run all scripts sequentially."""
    print("\n" + "="*80)
    print("  MASTER SCRIPT: Running Basecoins.py, Base.py, and refined.py")
    print(f"  Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Check if required files exist
    if not check_required_files():
        sys.exit(1)
    
    # Track results
    results = {}
    all_successful = True
    
    # Run Script 1: Basecoins.py
    results["Basecoins.py"] = run_script("Basecoins.py")
    if not results["Basecoins.py"]:
        all_successful = False
        print("\n[STOPPING] Basecoins.py failed. Not running subsequent scripts.\n")
        sys.exit(1)
    
    # Run Script 2: Base.py
    results["Base.py"] = run_script("Base.py")
    if not results["Base.py"]:
        all_successful = False
        print("\n[STOPPING] Base.py failed. Not running refined.py.\n")
        sys.exit(1)
    
    # Run Script 3: refined.py
    results["refined.py"] = run_script("refined.py")
    if not results["refined.py"]:
        all_successful = False
    
    # Final summary
    print("\n" + "="*80)
    print("  MASTER SCRIPT EXECUTION SUMMARY")
    print(f"  End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    for script, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"  {status:12} - {script}")
    
    print("="*80)
    
    if all_successful:
        print("\n✓ All scripts completed successfully!")
        print("\nGenerated files should include:")
        print("  - base.txt (from Basecoins.py)")
        print("  - gmgn_tokens.xlsx (from Basecoins.py)")
        print("  - base_results.json (from Base.py)")
        print("  - base_results.csv (from Base.py)")
        print("  - baserefined.csv (from refined.py)")
    else:
        print("\n✗ Some scripts failed. Check the output above for details.")
    
    print("\n" + "="*80 + "\n")
    
    sys.exit(0 if all_successful else 1)

if __name__ == "__main__":
    main()
