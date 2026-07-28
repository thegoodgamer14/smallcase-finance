#!/usr/bin/env bash
# Green-path demo: install → curated data → tests → next steps for API + UI.
# Usage (from repo root):  bash scripts/run_demo.sh   or   make demo
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> [1/4] Install Python package (editable + dev)"
python3 -m pip install -e ".[dev]"

echo "==> [2/4] Run data pipeline (raw → data/curated Parquet)"
python3 -m smallcase_finance.pipeline

echo "==> [3/4] Run tests"
python3 -m pytest -q

echo "==> [4/4] Ensure web dependencies"
if [[ ! -d apps/web/node_modules ]]; then
  (cd apps/web && npm install)
else
  echo "    apps/web/node_modules present — skip npm install"
fi

cat <<'EOF'

────────────────────────────────────────────────────────────
 Demo ready. Sample smallcases: digital-india, momentum-quality
────────────────────────────────────────────────────────────

Start (two terminals from repo root):

  make api    # FastAPI  → http://127.0.0.1:8000  (OpenAPI /docs)
  make web    # Next.js  → http://localhost:3000

Optional:
  curl -s http://127.0.0.1:8000/health | jq
  curl -s http://127.0.0.1:8000/smallcases | jq '.items[].id'

Env overrides:
  DATA_CURATED_ROOT   curated Parquet root (default: <repo>/data/curated)
  NEXT_PUBLIC_API_URL frontend API base     (default: http://127.0.0.1:8000)

Docs: README.md · docs/api.md · docs/data/pipeline.md
EOF
