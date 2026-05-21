# Massive Financial Data Plane

## What This Repo Provides

- An agent-based method for downloading market data with orchestration mediated
  by Blocks and an agent-facing Kanban board
- Chunked Massive download cards so multiple workers can share a nightly run
- Provider-aware pacing and retry behavior for long-running data jobs
- Parquet output written as each ticker finishes
- A staged handoff from download cards to simple public technical-feature cards
- A local fallback path that can run without Blocks on one machine
- A Blocks agent named `agent_massive_financial_data_plane` for seeding and
  inspecting financial data-plane work
- An MCP server that gives AI agents direct Massive market-data tools plus
  board-backed pipeline tools

This repo is a market-data workload built on top of the generic
`agent-work-boards` coordination layer. The Kanban board owns work state; these
workers own Massive downloads, Parquet writes, and the public feature example.
Massive is the current name for the service formerly known as Polygon.io; the
worker still accepts `POLYGON_API_KEY` and old `--polygon-*` flags for
compatibility.

For deployment mode choices, use the `agent-work-boards` deployment guide:
local SQLite for one-machine demos, Jira plus Brain plus PubNub for team
setups, and SSH RPC when worker machines should not run HTTP services.

## Dependency

Install the work-board package first. During local development from this split
directory layout:

```bash
python3.11 -m pip install -e ../agent-work-boards
python3.11 -m pip install -e .
```

After installation, console scripts are available:

```bash
massive-data-plane plan
massive-data-plane-demo --help
massive-prefetch-worker --help
massive-technicals-worker --help
massive-data-plane-request < request.json
massive-data-plane-mcp
```

Once the work-board package is published, this repo can depend on the published
package instead of the sibling directory.

## API Keys

Put runtime keys in a local `.env` file in this repo. Do not commit that file.

```bash
cp .env.example .env
```

Edit `.env`:

```text
MASSIVE_API_KEY=your-massive-key
```

`POLYGON_API_KEY` is still accepted as a compatibility fallback for older
accounts, but new setups should use `MASSIVE_API_KEY`.

If you are running the Blocks agent locally or publishing it, also put the
Blocks key in the Blocks agent directory:

```bash
cd agent_massive_financial_data_plane
blocks login --write-env
```

Jira-backed board usage also needs Jira settings in `.env`:

```text
JIRA_BASE_URL=https://your-site.atlassian.net
JIRA_PROJECT_KEY=AWQ
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=your-jira-token
```

## Flow

```text
strategy requests -> deduplicated symbol set -> chunked download cards
download workers -> ticker Parquet files -> technical-work cards
technical workers -> feature Parquet files
```

The public technical stage intentionally computes only a small feature set:
`return_1d`, `sma_20`, `atr_14`, and `rsi_14`.

## Local Nightly Example

Defaults are intentionally small for free Massive API keys: `2` symbols per
download card and `2` artifacts per technicals card. For a paid or higher-rate
setup, raise those with `--symbols-per-card 50` and `--artifacts-per-card 25`.

Run the full local pipeline without a Massive API key:

```bash
python3.11 data_plane/demo.py
```

That demo registers a four-symbol request, seeds two prefetch cards, starts two
prefetch worker processes, writes price Parquet artifacts incrementally, plans
technical-feature cards, starts two technical worker processes, and writes
public RSI 14 / ATR 14 feature Parquet artifacts. It uses deterministic demo
bars by default. To call Massive instead, provide `MASSIVE_API_KEY` in `.env`
and add `--live`.

```bash
python3.11 data_plane/nightly_plan.py register-file russell1000 ../v4.3.0/data/config/russell1000.csv --column ticker
python3.11 data_plane/nightly_plan.py seed-prefetch --start 2024-01-01 --end 2026-05-20 --backend sqlite --db-path data/nightly.sqlite
python3.11 data_plane/prefetch/worker.py --backend sqlite --db-path data/nightly.sqlite --board data-prefetch --worker-id prefetch-01 --limit 1 --min-symbol-seconds 4
python3.11 data_plane/technicals/planner.py --backend sqlite --db-path data/nightly.sqlite --board data-prefetch
python3.11 data_plane/technicals/worker.py --backend sqlite --db-path data/nightly.sqlite --board data-prefetch --worker-id technicals-01 --limit 1
```

Higher-throughput example:

```bash
python3.11 data_plane/nightly_plan.py seed-prefetch --start 2024-01-01 --end 2026-05-20 --backend sqlite --db-path data/nightly.sqlite --symbols-per-card 50
python3.11 data_plane/technicals/planner.py --backend sqlite --db-path data/nightly.sqlite --board data-prefetch --artifacts-per-card 25
```

In production, use Blocks to create, inspect, and move board cards while the
worker processes do the long-running data work. If Blocks is unavailable, the
same requests can be run with the Python CLIs against the same board.

## MCP Agent Access

Install the MCP extra when an AI agent should call Massive and the data plane as
tools:

```bash
python3.11 -m pip install -e ".[mcp]"
```

Run the server over stdio:

```bash
massive-data-plane-mcp
```

The MCP server exposes board tools such as `register_data_request`,
`seed_prefetch_cards`, and `data_plane_status`, plus direct market-data tools
such as `get_stock_bars`, `get_stock_last_quote`, `get_stock_last_trade`,
`get_stock_quotes`, and `get_stock_market_snapshot`.

See [docs/MCP.md](docs/MCP.md) for the full tool list.

## Blocks Agent

The Blocks package is under
[agent_massive_financial_data_plane](agent_massive_financial_data_plane). It is
intentionally an orchestration surface: it registers requested symbols, seeds
prefetch cards, plans technical-feature cards, and reports status. Long-running
downloads and feature generation stay in worker processes.

Example request:

```json
{
  "action": "seed_prefetch",
  "symbols": ["AAPL", "MSFT"],
  "start": "2024-01-01",
  "end": "2026-05-20",
  "backend": "sqlite",
  "db_path": "data/nightly.sqlite",
  "symbols_per_card": 2
}
```

## More

See [TICKER_WORKERS.md](TICKER_WORKERS.md) for worker commands, HTTP board
coordination, and local parallel fallback.

## Credentials

Runtime startup requires local environment variables or ignored `.env` files.
Users running their own copy must provide their own Massive and board
configuration.

Before publishing the repo, run:

```bash
python3.11 scripts/secret_scan.py
```

Use the release checklist in the sibling `agent-work-boards` repo before
publishing Python packages, Blocks agents, or git changes:

```text
../agent-work-boards/docs/RELEASE_CHECKLIST.md
```

## License

Copyright 2026 Sandra Carrico.

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and
[NOTICE](NOTICE).
