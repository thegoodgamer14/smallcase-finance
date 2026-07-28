.PHONY: install data pipeline clean-curated test api web demo sync-upstox

# Optional: YEARS=5 FROM=2020-01-01 TO=2025-12-31 SYMBOLS=TCS,INFY
YEARS ?=
FROM ?=
TO ?=
SYMBOLS ?=

# Python package + web deps (local-first)
install:
	python3 -m pip install -e ".[dev]"
	cd apps/web && npm install

# Generate sample raw (if needed) + rebuild all curated Parquet
data: pipeline

pipeline:
	python3 -m smallcase_finance.pipeline

# Remove curated outputs only (raw is never deleted by make)
clean-curated:
	find data/curated -name '*.parquet' -delete

# Local API (OpenAPI at http://127.0.0.1:8000/docs)
api:
	python3 -m uvicorn smallcase_finance.main:app --reload --app-dir src --host 127.0.0.1 --port 8000

# Next.js UI (http://localhost:3000) — requires API for live data
web:
	cd apps/web && npm run dev

test:
	python3 -m pytest -q

# Upstox historical prices → raw drop → pipeline
# Examples:
#   make sync-upstox
#   make sync-upstox YEARS=5
#   make sync-upstox FROM=2021-01-01 TO=2024-12-31
#   make sync-upstox SYMBOLS=TCS,INFY YEARS=2
# Without UPSTOX_ACCESS_TOKEN, falls back to sample data then still runs pipeline.
sync-upstox:
	@ARGS=""; \
	if [ -n "$(YEARS)" ]; then ARGS="$$ARGS --years $(YEARS)"; fi; \
	if [ -n "$(FROM)" ]; then ARGS="$$ARGS --from $(FROM)"; fi; \
	if [ -n "$(TO)" ]; then ARGS="$$ARGS --to $(TO)"; fi; \
	if [ -n "$(SYMBOLS)" ]; then ARGS="$$ARGS --symbols $(SYMBOLS)"; fi; \
	python3 -m smallcase_finance.integrations.upstox $$ARGS --pipeline

# One-shot green path: install → pipeline → test → print how to run api/web
demo:
	bash scripts/run_demo.sh
