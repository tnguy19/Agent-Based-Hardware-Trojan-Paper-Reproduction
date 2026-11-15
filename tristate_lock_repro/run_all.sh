#!/usr/bin/env bash
# Reproduce everything (about 1-2 minutes on 2 cores).
set -euo pipefail
cd "$(dirname "$0")"
python -m unittest discover -s tests            # 11 tests
python run_experiments.py --exp main half model # 840 runs -> results/raw_results.csv
python analyze.py                               # tables + figures -> results/
python run_sat_attack.py                        # supplementary SAT attack -> results/sat_attack.csv
python lockforge/evaluate_bcsrp.py              # LockForge local-execution score
