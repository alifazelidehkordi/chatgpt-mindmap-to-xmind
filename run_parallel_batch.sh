#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

START1="${START1:-1}"
END1="${END1:-10}"
START2="${START2:-11}"
END2="${END2:-20}"

mkdir -p logs downloads downloads_worker2 chrome_profile_worker2

echo "=== Mind Map v3 Parallel Batch: 2 workers ==="
echo "worker1: files ${START1}-${END1} -> logs/batch_run_worker1.log"
echo "worker2: files ${START2}-${END2} -> logs/batch_run_worker2.log"
echo ""

CHATGPT_DOWNLOAD_DIR="$PWD/downloads" \
CHATGPT_RUN_LOG="$PWD/run_worker1.log" \
./run_pdf_batch.sh --save-diagnostics --start-index "$START1" --end-index "$END1" \
  2>&1 | tee logs/batch_run_worker1.log &
pid1=$!

CHATGPT_CHROME_PROFILE_DIR="$PWD/chrome_profile_worker2" \
CHATGPT_DOWNLOAD_DIR="$PWD/downloads_worker2" \
CHATGPT_RUN_LOG="$PWD/run_worker2.log" \
./run_pdf_batch.sh --save-diagnostics --start-index "$START2" --end-index "$END2" \
  2>&1 | tee logs/batch_run_worker2.log &
pid2=$!

set +e
wait "$pid1"
status1=$?
wait "$pid2"
status2=$?
set -e

if [[ "$status1" -ne 0 || "$status2" -ne 0 ]]; then
  echo "worker1 exit: $status1"
  echo "worker2 exit: $status2"
  exit 1
fi

echo "Both workers finished."