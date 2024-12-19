#!/bin/bash
set -eo pipefai


echo "Starting data processing..."
echo "Step 1: Running Python cleaning script"
python3 step-1-clean.py

echo "Step 2: Running bash processing script"
bash sleep-data-cleaned-sample.bash

echo "Step 3: analyzing..."
python3 step-2-analyze.py

echo "Processing complete!"
