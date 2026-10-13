#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec python3 -m lead_review serve
