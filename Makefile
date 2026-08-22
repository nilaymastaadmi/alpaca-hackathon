# Judge-facing entry points. Everything here is runnable without credentials
# except `decide`, which needs .env.

.PHONY: test verify seal summary decide dry-run

test:
	uv run --with pytest --with tzdata --with requests python -m pytest tests/ -q

## Recompute the Merkle root over every logged decision and compare it to the
## sealed value. This is the point of the artifact log: you do not have to
## trust the operator, you can check.
verify:
	uv run --with requests python agent/artifacts.py verify

seal:
	uv run --with requests python agent/artifacts.py seal

summary:
	uv run --with requests python agent/artifacts.py summary

dry-run:
	uv run --with requests --with tzdata python agent/agent.py --dry-run

decide:
	uv run --with requests --with tzdata python agent/agent.py

## Local dashboard. Reads artifacts off disk, so it renders with the market
## closed and the API down.
dash:
	uv run --with streamlit --with pandas streamlit run dashboard/app.py
