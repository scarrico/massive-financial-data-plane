# Massive Financial Data Plane Blocks Agent

Apache-2.0 licensed. Copyright 2026 Sandra Carrico.

This Blocks agent coordinates Massive financial market-data jobs through Agent
Work Boards. It seeds and inspects work cards; long-running downloads and
technical-feature generation should run in Python worker processes.

Example request:

```json
{
  "action": "seed_prefetch",
  "symbols": ["AAPL", "MSFT"],
  "start": "2024-01-01",
  "end": "2026-05-20",
  "backend": "sqlite",
  "db_path": "data/nightly.sqlite"
}
```
