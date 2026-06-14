from __future__ import annotations
# pyright: reportAny=false, reportUnusedCallResult=false

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent


def run_step(script_name: str) -> None:
    script_path = SCRIPT_DIR / script_name
    result = subprocess.run([sys.executable, str(script_path)], cwd=ROOT, text=True, capture_output=True, check=False)
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, end="")
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--load-neo4j", action="store_true")
    args = parser.parse_args()

    run_step("build_integrated_data.py")
    run_step("validate_data.py")
    run_step("export_neo4j_import_files.py")
    run_step("validate_data.py")
    if args.load_neo4j:
        run_step("load_neo4j.py")
    print("Pipeline complete")


if __name__ == "__main__":
    main()
