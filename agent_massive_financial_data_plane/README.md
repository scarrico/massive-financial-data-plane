# Massive Financial Data Plane Blocks Agent

Apache-2.0 licensed. Copyright 2026 Sandra Carrico.

This Blocks agent coordinates Massive financial market-data jobs through Agent
Work Boards. It seeds and inspects work cards; long-running downloads and
technical-feature generation should run in Python worker processes.

## How It Fits With Agent Work Boards

This agent is the market-data workload entrypoint. It does not replace Kanban or
Scrum. It creates and inspects financial data-plane cards on an Agent Work Board,
then Python workers claim those cards to download Massive data and calculate
public example technicals.

Use `agent_kanban_board` for general board operations, `agent_brain` for mutable
instructions and remembered summaries, and this agent for market-data planning.

## Runtime Keys

For local development, put keys in ignored `.env` files:

```bash
cd ..
cp .env.example .env
# edit .env and set MASSIVE_API_KEY

cd agent_massive_financial_data_plane
blocks login --write-env
```

The first `.env` is for the Massive data workers. The second is for the Blocks
runner/publisher.

Example request:

```json
{
  "action": "seed_prefetch",
  "symbols": ["AAPL", "MSFT"],
  "start": "2024-01-01",
  "end": "2026-05-20",
  "backend": "sqlite",
  "board_id": "market-data-nightly",
  "db_path": "data/nightly.sqlite",
  "symbols_per_card": 2
}
```

For paid or higher-rate Massive usage, set `"symbols_per_card": 50`.
