#!/bin/sh
# Start real GPIO control from this script's directory.
set -eu
cd "$(dirname "$0")"
exec python3 main.py --hardware
