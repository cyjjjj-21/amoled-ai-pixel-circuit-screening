#!/usr/bin/env python3
"""Run tests, finite screening, behavioral SPICE, and the V3 report; fail fast."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    for dependency in ("numpy", "matplotlib"):
        if importlib.util.find_spec(dependency) is None:
            raise SystemExit(f"Missing {dependency}; install requirements-plot.txt first.")
    if shutil.which("ngspice") is None:
        raise SystemExit("Missing ngspice; install it and add it to PATH first.")
    root = Path(__file__).resolve().parent
    steps = [
        ["-m", "unittest", "-v"], ["screen.py"], ["validate_v3_spice.py"],
        ["build_v3_figures.py"], ["plot_v3_waveforms.py"], ["build_v3_report.py"],
        ["tools/check_results_v3.py"],
    ]
    for step in steps:
        print("Running: " + " ".join(step), flush=True)
        subprocess.run([sys.executable, *step], cwd=root, check=True)
    print("Complete: results_v3/REPORT.md")


if __name__ == "__main__":
    main()
