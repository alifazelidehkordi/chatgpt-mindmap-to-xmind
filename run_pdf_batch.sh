#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=== ChatGPT Mind Map v3 — PDF/DOCX Batch (Linux) ==="
echo "Project dir: $(pwd)"

VENV_DIR=".venv-linux"
PYTHON="${VENV_DIR}/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
  echo "Python venv not found. Running setup.sh..."
  ./setup.sh
fi

if ! "${PYTHON}" -c "import patchright, playwright_stealth" 2>/dev/null; then
  echo "Dependencies missing. Reinstalling..."
  "${PYTHON}" -m pip install --upgrade pip
  "${PYTHON}" -m pip install -r requirements.txt
  "${PYTHON}" -m patchright install chromium
fi

INPUT_DIR="${INPUT_DIR:-inputs}"
OUTPUT_DIR="${OUTPUT_DIR:-outputs/opml}"
PROMPT_FILE="${PROMPT_FILE:-prompts/prompt-mind-map.md}"
RESPONSE_TIMEOUT="${RESPONSE_TIMEOUT:-600}"
DOWNLOAD_TIMEOUT="${DOWNLOAD_TIMEOUT:-120}"
SKIP_WARMUP="${SKIP_WARMUP:-1}"
export LONG_GENERATION_STOP_SECONDS="${LONG_GENERATION_STOP_SECONDS:-900}"
export POST_STOP_GRACE_SECONDS="${POST_STOP_GRACE_SECONDS:-60}"

mkdir -p "${OUTPUT_DIR}" downloads logs

echo ""
echo "Input dir  : ${INPUT_DIR}"
echo "Output dir : ${OUTPUT_DIR}"
echo "Prompt     : ${PROMPT_FILE}"
echo ""

ARGS=(
  --input-dir "${INPUT_DIR}"
  --output-dir "${OUTPUT_DIR}"
  --prompt "${PROMPT_FILE}"
  --response-timeout "${RESPONSE_TIMEOUT}"
  --download-timeout "${DOWNLOAD_TIMEOUT}"
)
if [[ "${SKIP_WARMUP}" == "1" ]]; then
  ARGS+=(--no-warm-up)
fi

"${PYTHON}" scripts/batch_pdf.py "${ARGS[@]}" "$@"

EXIT_CODE=$?
echo "Batch finished with exit code: ${EXIT_CODE}"
echo "Results: ${OUTPUT_DIR}/"
exit $EXIT_CODE