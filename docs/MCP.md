# MCP Server

This repo exposes Massive market-data access and data-plane orchestration as MCP
tools for AI agents.

## Install

```bash
python3.11 -m pip install -e "../agent-work-boards[brain]"
python3.11 -m pip install -e ".[mcp]"
```

The MCP server reads runtime configuration from environment variables or `.env`.
Live Massive calls require:

```text
MASSIVE_API_KEY=your-massive-key
```

## Run

```bash
massive-data-plane-mcp
```

Equivalent source-tree command:

```bash
python3.11 -m data_plane.mcp_server
```

## Tools

Board and pipeline tools:

- `register_data_request`
- `plan_requested_symbols`
- `seed_prefetch_cards`
- `plan_technical_cards`
- `data_plane_status`

Direct market-data tools:

- `get_stock_bars`
- `write_stock_bars_parquet`
- `get_stock_last_quote`
- `get_stock_last_trade`
- `get_stock_quotes`
- `get_stock_market_snapshot`

`write_stock_bars_parquet` accepts `live=false` for deterministic demo bars.
Live quote, trade, snapshot, and historical-bar tools call Massive and require a
Massive API key with access to the requested endpoint.

## Agent Use

Use the board tools when the agent should create durable work for workers.
Use the direct market-data tools when the agent needs a small answer immediately,
such as a latest quote, a recent trade, or a short bar sample.
