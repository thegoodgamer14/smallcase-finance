.PHONY: install data pipeline clean-curated test api web demo sync-upstox kite-login kite-exchange kite-holdings kite-profile upstox-status

# Optional: YEARS=5 FROM=2020-01-01 TO=2025-12-31 SYMBOLS=TCS,INFY STRICT=1
YEARS ?=
FROM ?=
TO ?=
SYMBOLS ?=
STRICT ?=

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

# Check whether UPSTOX_ACCESS_TOKEN is present (never prints the token)
upstox-status:
	@python3 -c "from smallcase_finance.config import upstox_configured, UPSTOX_DEFAULT_YEARS; \
print('upstox_configured=', upstox_configured()); \
print('default_years=', UPSTOX_DEFAULT_YEARS); \
print('docs=docs/integrations/upstox.md')"

# Upstox historical prices → raw drop → pipeline (sole market-data path)
# Examples:
#   make sync-upstox
#   make sync-upstox YEARS=5
#   make sync-upstox FROM=2021-01-01 TO=2024-12-31
#   make sync-upstox SYMBOLS=TCS,INFY YEARS=2
#   make sync-upstox YEARS=3 STRICT=1   # fail if no token / no bars (no sample)
# Without token: sample demo fallback unless STRICT=1.
sync-upstox:
	@ARGS=""; \
	if [ -n "$(YEARS)" ]; then ARGS="$$ARGS --years $(YEARS)"; fi; \
	if [ -n "$(FROM)" ]; then ARGS="$$ARGS --from $(FROM)"; fi; \
	if [ -n "$(TO)" ]; then ARGS="$$ARGS --to $(TO)"; fi; \
	if [ -n "$(SYMBOLS)" ]; then ARGS="$$ARGS --symbols $(SYMBOLS)"; fi; \
	if [ "$(STRICT)" = "1" ]; then ARGS="$$ARGS --no-sample-fallback"; fi; \
	python3 -m smallcase_finance.integrations.upstox $$ARGS --pipeline

# Kite Connect (equity holdings — NOT a price source)
# Access token is NOT from the developer console: login flow only.
#   make kite-login
#   # browser → redirect with request_token=
#   make kite-exchange REQUEST_TOKEN=...
#   make kite-holdings
REQUEST_TOKEN ?=
kite-login:
	python3 -m smallcase_finance.integrations.kite login

kite-exchange:
	@if [ -z "$(REQUEST_TOKEN)" ]; then echo "Usage: make kite-exchange REQUEST_TOKEN=..."; exit 1; fi
	python3 -m smallcase_finance.integrations.kite exchange --request-token "$(REQUEST_TOKEN)"

kite-holdings:
	python3 -m smallcase_finance.integrations.kite holdings

kite-profile:
	python3 -m smallcase_finance.integrations.kite profile

# One-shot green path: install → pipeline → test → print how to run api/web
demo:
	bash scripts/run_demo.sh
