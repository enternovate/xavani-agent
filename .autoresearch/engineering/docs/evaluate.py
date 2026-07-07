#!/usr/bin/env python3
"""Measure Docusaurus docs site build success.
DO NOT MODIFY after experiment starts — this is the fixed evaluator."""

import re
import subprocess
import sys

# --- CONFIGURE THESE ---
BUILD_CMD = "cd /Users/andilemushwana/xavani-agent/website && npm run build 2>&1 | tail -5"
# --- END CONFIG ---

result = subprocess.run(BUILD_CMD, shell=True, capture_output=True, text=True, timeout=300)
output = result.stdout + "\n" + result.stderr

# Build succeeded if exit code == 0 and no ERROR lines
if result.returncode == 0 and "ERROR" not in output:
    build_status = 1.0
    print(f"build_status: {build_status:.4f}")
    print("build_success: 1")
    print("build_errors: 0")
else:
    # Count errors
    errors = len(re.findall(r"\[ERROR\]", output))
    build_status = max(0.0, 1.0 - (errors * 0.1))
    print(f"build_status: {build_status:.4f}")
    print(f"build_success: 0")
    print(f"build_errors: {errors}")
    if result.returncode != 0:
        sys.exit(1)
