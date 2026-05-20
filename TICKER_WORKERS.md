# Data Plane Prefetch Demo

This is the first practical Kanban workload: market-data prefetch jobs.

Run the end-to-end local demo first:

```bash
python3.11 data_plane/demo.py
```

It starts multiple local worker processes, writes price Parquet files, moves
download cards to `technicals`, plans public technical-feature cards, and writes
feature Parquet files. It uses deterministic demo bars unless `--live` is set.

Register symbols requested by a strategy:

```bash
python3.11 data_plane/nightly_plan.py register example-strategy AAPL MSFT SPY
```

Preview the nightly symbol set:

```bash
python3.11 data_plane/nightly_plan.py plan
```

Seed prefetch jobs from registered requests:

```bash
python3.11 data_plane/nightly_plan.py seed-prefetch --start 2024-01-01 --end 2026-05-20 --backend sqlite --db-path data/nightly.sqlite
```

Seed jobs onto Jira/Kanban:

```bash
python3.11 data_plane/prefetch/seed_jobs.py AAPL MSFT SPY --board data-prefetch --priority 10
```

`--symbols-per-card` defaults to `2` so a free Massive API key can run a small
demo without creating oversized download cards. For a paid or higher-rate setup,
use `--symbols-per-card 50`.

Run workers:

```bash
python3.11 data_plane/prefetch/worker.py --board data-prefetch --worker-id worker-01 --limit 2
python3.11 data_plane/prefetch/worker.py --board data-prefetch --worker-id worker-02 --limit 2
```

Successful prefetch cards move to `technicals`. Split a downloaded card into
smaller technical-work cards:

```bash
python3.11 data_plane/technicals/planner.py --board data-prefetch --worker-id technicals-planner
```

`--artifacts-per-card` defaults to `2`. For higher-throughput feature work, use
`--artifacts-per-card 25`.

Run public feature workers against those cards:

```bash
python3.11 data_plane/technicals/worker.py --board data-prefetch --worker-id technicals-01 --limit 1
python3.11 data_plane/technicals/worker.py --board data-prefetch --worker-id technicals-02 --limit 1
```

Use plain parallel fallback without Jira/Kanban:

```bash
python3.11 data_plane/prefetch/parallel_runner.py AAPL MSFT SPY --workers 3
```

Use auto mode. This tries Jira/Kanban first and falls back to local parallel
workers if Kanban is unavailable:

```bash
python3.11 data_plane/prefetch/run.py AAPL MSFT SPY --workers 3 --mode auto
```

Use a shared HTTP board for cross-machine workers:

```bash
python3.11 -m kanban.http_server --host 0.0.0.0 --port 8765 --backend sqlite --db-path data/kanban.sqlite
python3.11 data_plane/prefetch/seed_jobs.py AAPL MSFT SPY --board-client http --board-url http://BOARD_HOST:8765 --board data-prefetch
python3.11 data_plane/prefetch/worker.py --board-client http --board-url http://BOARD_HOST:8765 --board data-prefetch --worker-id worker-01 --limit 2
```

Use SSH instead of HTTP when the board lives on another developer machine and no
HTTP service is running:

```bash
python3.11 data_plane/prefetch/seed_jobs.py AAPL MSFT SPY \
  --board-client ssh \
  --ssh-host 10.0.0.5 \
  --ssh-user your-user \
  --ssh-key /path/to/private/key \
  --ssh-root /path/to/agent-work-boards \
  --backend sqlite \
  --db-path data/kanban.sqlite \
  --board data-prefetch

python3.11 data_plane/prefetch/worker.py \
  --board-client ssh \
  --ssh-host 10.0.0.5 \
  --ssh-user your-user \
  --ssh-key /path/to/private/key \
  --ssh-root /path/to/agent-work-boards \
  --backend sqlite \
  --db-path data/kanban.sqlite \
  --board data-prefetch \
  --worker-id worker-01 \
  --limit 2
```

The SQLite board file stays on the SSH target. Workers do not mount or share
the database file; they execute board operations on the remote host.

Run medium-lived addressable agent processes:

```bash
python3.11 -m agent_runtime.supervisor \
  --module data_plane.prefetch.agent \
  --agents 3 \
  --board data-prefetch \
  --transport local \
  --max-cards 1
```

Inspect local agents:

```bash
python3.11 -m agent_runtime.agentctl --registry-db agent_runtime.sqlite agents
```

The current worker fetches Massive aggregates and writes Parquet artifacts to:

```text
data/data_plane/prefetch/
```

Runtime requires:

```text
MASSIVE_API_KEY
```

`POLYGON_API_KEY` is still accepted as a compatibility fallback for accounts and
scripts created before the Polygon.io rebrand.

Put the key in a local ignored `.env` file:

```bash
cp .env.example .env
```

Then edit `.env`:

```text
MASSIVE_API_KEY=your-massive-key
```

The Massive Python client examples use `limit=50000` for aggregate bars,
and their README recommends using the maximum supported limit for large datasets
to reduce API calls. The prefetch runner defaults to:

```text
--massive-limit 50000
```

Rate limiting is configurable. Massive pricing currently lists the free stocks
plan at 5 API calls/minute. The old Polygon.io knowledge-base article says paid
plans have unlimited API calls but recommends staying under 100 requests/second
to avoid throttling. This project defaults conservatively to:

```text
--massive-calls-per-minute 60
```

For a free plan, use:

```text
--massive-calls-per-minute 5
```

Technical feature generation should be a separate data-plane stage.
