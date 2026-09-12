# Real-Time Crypto Trading Stack

A tick-to-signal research and paper-trading system for Binance spot markets. It ingests live
order-book updates for 10 pairs, maintains an inventory-aware fair value per asset, runs three
signal models over 1-second bars, sizes and executes paper orders under explicit risk limits,
and streams the resulting positions and PnL to a live dashboard.

Built in Python 3.12 (asyncio, Numba, FastAPI, SQLAlchemy) with a React + Vite frontend,
Postgres/TimescaleDB for persistence and Redis for real-time fan-out.

- **Universe:** BTC, ETH, XRP, BNB, SOL, TRX, DOGE, ADA, LINK, DOT — all `USDT` spot pairs.
- **Fair value:** Avellaneda–Stoikov-style reservation price built from the microprice, an
  order-book-imbalance skew and an inventory risk penalty.
- **Signals:** moving-average crossover, momentum (ROC) and engulfing candlestick pattern,
  combined by vote into one equal-weight target per asset.
- **Execution:** volatility-targeted sizing capped by participation rate, with a fee and
  market-impact cost model and a one-trade-per-minute-per-asset throttle.
- **Status:** paper trading. The engine simulates fills against top of book; it does not place
  orders on any venue.

---

## Architecture

```
                    ┌──────────────────────── Binance ────────────────────────┐
                    │  REST /api/v3/klines            WS @bookTicker (x10)    │
                    └────────────┬───────────────────────────┬────────────────┘
                                 │ cold start                │ hot path
                                 ▼                           ▼
                          BinanceRest                  BinanceDriver
                    (pagination, 429/418,             (tenacity backoff,
                     Retry-After honoured)             multiplexed stream)
                                 │                           │
                                 │                           ▼
                                 │                      DataGuard          per-symbol
                                 │              (dedup + monotonicity)     dedup state
                                 │                           │
                                 ▼                           ▼
                          MarketState  ◄──────────── asyncio.Queue
                     (deque of closed bars,                  │
                      current bar mutable)                   ▼
                                 │                   RealTimeProcessor
                                 │              (1s bar aggregation, warm-up,
                                 │               orchestrates decision cycle)
                                 │                           │
                                 └──────────────┬────────────┘
                                                ▼
                                       PortfolioManager
                            MA crossover · Momentum · Engulfing  (Numba kernels)
                                                │  consolidated signal ∈ {-1,0,1}
                                                ▼
                                          ReservePrice  ──► fair value, σ
                                                │
                                                ▼
                                          TraderEngine
                              sizing (Q*) · risk caps · throttle · ledger
                                                │
                          ┌─────────────────────┴─────────────────────┐
                          ▼                                           ▼
                  Postgres / TimescaleDB                      Redis pub/sub
                  (candles, trades, ticks)                  (ticks, trades, state)
                          │                                           │
                          └─────────────────┬─────────────────────────┘
                                            ▼
                                     FastAPI  (REST + /ws/live)
                                            │
                                            ▼
                                    React + Vite dashboard
```

| Stage | Module |
|---|---|
| REST historical loader | [`src/adapters/rest/binance_rest.py`](src/adapters/rest/binance_rest.py) |
| WebSocket driver, dedup guard | [`src/adapters/socket/binance_socket.py`](src/adapters/socket/binance_socket.py) |
| Exchange port (ABC) | [`src/interfaces/data_provider.py`](src/interfaces/data_provider.py) |
| Bar state (history + live bar) | [`src/core/market_state.py`](src/core/market_state.py) |
| Fair value / volatility | [`src/core/reserve_price.py`](src/core/reserve_price.py) |
| Signal aggregation | [`src/core/strategies/portfolio_manager.py`](src/core/strategies/portfolio_manager.py) |
| Numba signal kernels | [`src/core/strategies/math_numba.py`](src/core/strategies/math_numba.py) |
| Sizing, risk, ledger | [`src/core/trader_engine.py`](src/core/trader_engine.py) |
| Per-symbol orchestration | [`src/core/realtime_processor.py`](src/core/realtime_processor.py) |
| Persistence | [`src/database/`](src/database/) |
| Message bus | [`src/infrastructure/redis_bus.py`](src/infrastructure/redis_bus.py) |
| API | [`src/api/`](src/api/) |
| Dashboard | [`frontend/src/`](frontend/src/) |

---

## The quantitative model

### Fair value

Binance `@bookTicker` gives best bid/ask and their sizes on every book update. Rather than the
naive mid, the engine uses the **microprice**, which weights each side by the opposite side's
size and is the better short-horizon predictor of the next trade price:

```
P_micro = (Q_bid · P_bid + Q_ask · P_ask) / (Q_bid + Q_ask)
```

**Volatility** is an EWMA of log returns on the simple mid, sampled at 1 Hz, using the
RiskMetrics recursion with λ = 0.94:

```
σ²_t = (1 − λ) · r²_t + λ · σ²_{t−1}     r_t = ln(P_t / P_{t−1})
```

The **reservation price** shifts fair value away from inventory risk and towards short-term
order-flow pressure:

```
p_r = P_micro + θ · OBI − q · γ · σ²

  OBI = (Q_bid − Q_ask) / (Q_bid + Q_ask)     order-book imbalance ∈ [−1, 1]
  θ   = current spread                        converts imbalance into price units
  q   = current inventory in the asset        signed, fed back from the engine
  γ   = 0.5                                   risk aversion
```

The inventory term is the Avellaneda–Stoikov skew: holding a long position pushes the
reservation price down, so the system becomes progressively less willing to add and more willing
to reduce — mean-reverting inventory towards zero without a separate flattening rule. The OBI
term is the alpha overlay: a book leaning bid-heavy lifts fair value within the spread.

`q` is read back from the execution engine on every decision cycle, so pricing and inventory form
a closed loop rather than two independent estimates.

### Costs

The reservation price above is a market maker's valuation. The engine crosses the spread, so it
is charged as a taker:

```
effective price = P_mkt ± (½ · spread + fee + impact)
impact = γ_impact · σ · √(Q / V)
```

The square-root impact law is standard; `γ_impact` is calibratable and is not calibrated here —
a fixed coefficient is used, which is the main known approximation in the cost model.

### Sizing

The closed-form optimum for a linear-edge / square-root-impact profit function,

```
π(Q) = Q·δ − Q·(γ·σ·√(Q/V))     ⇒     Q* = (4/9) · δ² · V / (γ·σ)²
```

was implemented first and **discarded**: with realistic magnitudes for `δ` and `σ` it is
numerically unstable — the quotient blows up whenever volatility approaches zero, producing
order sizes far beyond available capital.

What ships instead is volatility targeting scaled by a standardised edge and capped by
participation rate:

```
edge = |p_r − P_mkt| / (P_mkt · σ)        how many σ the market is from fair value
base = RiskBudget / (P_mkt · σ)           position size for a 1σ move ≈ RiskBudget
Q*   = min( base · edge , 0.10 · V )      capped at 10% of bar volume
```

`RiskBudget` defaults to 100 USDT per trade against 10,000 USDT of capital per asset. Sizing is
therefore proportional to conviction (`edge`) and inversely proportional to risk (`σ`), and can
never demand more than a tenth of the liquidity actually traded in the bar.

Three further constraints apply before any fill
([`trader_engine.py`](src/core/trader_engine.py)): at most one trade per asset per 60 seconds;
no single order above 10% of account equity; and no buy beyond cash on hand, no sell beyond
inventory held (spot only, no shorting).

---

## Signals

Three independent models vote on each closed bar; the sign of the sum is the target signal.
Each is a Numba `@njit` kernel operating on preallocated NumPy arrays.

| Model | Logic | Parameters |
|---|---|---|
| MA crossover | fast SMA crossing slow SMA | `fast`, `slow` |
| Momentum | rate of change over a lookback vs. a threshold | `period`, `threshold` |
| Engulfing | two-bar bullish/bearish engulfing body pattern | — |

Parameters are fitted per symbol by vectorised grid search over historical bars
([`Testeo_Strats/optimizer.py`](Testeo_Strats/optimizer.py), backtest kernels in
[`math_numba.py`](src/core/strategies/math_numba.py)) and written to
[`src/config/strategy_params.json`](src/config/strategy_params.json), which the portfolio manager
loads at startup. Every symbol therefore runs its own calibration — BTC trades a 9/20 crossover,
XRP a 19/90.

Aggregation is an unweighted vote across the three models, and capital is allocated equally
across the universe: each asset runs an independent engine with the same starting capital and the
same risk budget. No cross-asset correlation or covariance targeting is applied.

Signals are evaluated **only on closed bars**, after a warm-up period, and only on bars built from
live WebSocket data — never on the REST backfill. This removes the single largest source of
phantom backtest edge, which is acting on a bar that is still forming.

---

## Engineering notes

**Ingestion.** One multiplexed WebSocket connection carries all 10 symbols
(`/stream?streams=...`) rather than one connection per asset, so adding symbols costs a longer URL
rather than another socket. Reconnection is `tenacity` exponential backoff (1 → 10 s) retrying on
`ConnectionClosed`, `OSError`, `TimeoutError` and `WebSocketException`, with `ping_interval` /
`ping_timeout` set so a silently dead TCP connection is detected rather than hanging.

**REST resilience.** [`binance_rest.py`](src/adapters/rest/binance_rest.py) handles the two
rate-limit codes that matter on Binance explicitly: `429` (too many requests) and `418` (IP ban),
both by reading the `Retry-After` header the exchange returns rather than guessing a backoff.
Historical download is paginated forward by `startTime` at 1000 bars per request.

**Deduplication.** A per-symbol `DataGuard` drops a tick whose bid/ask prices and sizes are all
identical to the previous one — the book republishing without changing — so unchanged state never
triggers a strategy recomputation.

**Persistence.** Postgres (TimescaleDB image) over SQLAlchemy 2.0 async + asyncpg. Three tables:
`market_ticks` (book snapshots with reservation price and volatility), `candles` (OHLCV plus
volatility) and `trades` (side, price, qty, realised edge, theoretical `Q*`), with composite
indexes on `(symbol, time)` for the range queries the dashboard issues. Writes are batched.

**Real-time fan-out.** Redis pub/sub carries ticks and trade events from the engine to the API,
which relays them over a single WebSocket (`/ws/live`) to every connected browser. The dashboard
never polls for live prices.

**Python-level design.** Three deliberate uses of the language's extension points:

- A `@measure_latency` decorator ([`base.py`](src/core/strategies/base.py)) wraps every strategy's
  `calculate()`. It costs two `perf_counter_ns()` calls and a dict update, preserves the wrapped
  signature and docstring via `functools.wraps`, and accumulates count / total / max per function,
  readable at any time through `get_latency_stats()`. The numbers under *Performance* below come
  from it.
- A `StrategyMeta` metaclass validates at class-creation time that every strategy declares a
  unique uppercase `ID`. A malformed strategy fails at import, not at the first tick in
  production.
- `Candle.__lt__` and `Candle.__sub__` give bars natural chronological ordering and a
  `bar_a - bar_b` price delta; `__slots__` on `Candle`, `Registro` and `TraderEngine` removes the
  per-instance `__dict__`, which is what makes a large symbol universe affordable in memory.

---

## Technology choices

**Postgres over the alternatives.** Five storage backends were benchmarked on identical
synthetic tick streams ([`Justificaciones_Uso/Almacenamiento/`](Justificaciones_Uso/Almacenamiento/)).
CSV, SQLite and Parquet were fastest — they write straight to local disk — but that is exactly
what disqualifies them: bounded by one machine's disk, no replication, no concurrent readers.
MongoDB was acceptable on throughput but does not enforce synchronous durability by default.
Postgres sustained ~5,000 ticks/s against a peak inbound rate of ~1,000 ticks/s across the
universe: enough headroom, with client-server access, real transactions and a scaling path.
The TimescaleDB image was chosen over plain Postgres to keep hypertable partitioning available
as tick volume grows.

**Redis over Kafka.** At 10 symbols and ~1k msg/s, Kafka's partition management, broker
operations and consumer-group complexity buy nothing. Redis provides the pub/sub fan-out and
shared state the dashboard needs in a single container. Kafka becomes the right answer at the
point where multiple independent consumer applications need replayable, durably partitioned
history — which is a deliberate future migration, not a current need.

**React + Vite over Streamlit / Dash.** Streamlit re-executes the script on every interaction and
Dash round-trips callbacks through the server; both couple rendering to the server's event loop.
A trading dashboard showing a live book must never block on a chart redraw. React renders from a
WebSocket push with client-side state, so the ingestion path and the UI are fully decoupled, and
`lightweight-charts` gives candlestick rendering at the quality traders expect. The cost is a
build step and hand-written data plumbing rather than a one-file script.

---

## Running it

**Prerequisites:** Docker + Docker Compose, Python 3.12 with [`uv`](https://docs.astral.sh/uv/),
Node 20.

```bash
uv sync                       # Python environment from uv.lock
docker compose up -d          # Postgres/TimescaleDB, Redis, Mongo, API, frontend
./start.sh                    # infrastructure + ingestor + persister + dev frontend
```

| Service | Port | Notes |
|---|---|---|
| Dashboard | 3000 (Docker) / 5173 (dev) | React + Vite |
| API | 8000 | OpenAPI docs at `/docs` |
| Postgres / TimescaleDB | 5432 | |
| Redis | 6379 | |

`./stop.sh` tears everything down. **It also truncates the data tables** — see *Limitations*.

Run the ingestor alone against a live feed:

```bash
PYTHONPATH=. python apps/ingestor.py
```

Refit strategy parameters:

```bash
PYTHONPATH=. python Testeo_Strats/optimizer.py     # rewrites src/config/strategy_params.json
```

### API

| Endpoint | Returns |
|---|---|
| `GET /api/candles/{symbol}` | OHLCV history |
| `GET /api/ticks/{symbol}` | bid/ask history |
| `GET /api/trades` | executed trade ledger |
| `GET /api/positions` | live inventory per asset |
| `GET /api/pnl` | mark-to-market equity and return |
| `GET /api/symbols`, `/api/strategies`, `/api/strategy-params` | universe and configuration |
| `WS /ws/live` | live tick and trade stream |

---

## Repository layout

| Path | Contents |
|---|---|
| `src/core/` | Domain: bar state, fair value, strategies, execution engine |
| `src/adapters/` | Binance REST and WebSocket adapters |
| `src/interfaces/` | Exchange port |
| `src/database/` | SQLAlchemy models and async repository |
| `src/infrastructure/` | Redis bus |
| `src/api/` | FastAPI app, routes, response schemas |
| `apps/` | `ingestor.py`, `persister.py` entry points |
| `frontend/` | React + Vite dashboard |
| `Testeo_Strats/` | Parameter grid search |
| `Justificaciones_Uso/` | Storage backend benchmarks |
| `Latency_Tests/` | Latency/throughput harness and profiling suite |
| `tests/` | Simulation harnesses |
| `terraform/`, `docker/` | Single-node AWS deployment, container builds |

---

## Performance

Strategy evaluation, measured by the shipped `@measure_latency` decorator over 20,000 warm calls
per model on a 1,000-bar window (post-JIT, excluding compilation):

| Model | Mean | Max |
|---|---|---|
| MA crossover | 0.44 µs | 23.6 µs |
| Momentum | 0.42 µs | 25.6 µs |
| Engulfing | 0.43 µs | 20.0 µs |

A full three-model decision cycle costs ~1.3 µs, against a bar period of 1 s — signal evaluation
is nowhere near the bottleneck, which is the point of pushing the kernels through Numba. The
dominant costs are I/O: the database write and the WebSocket hop.

[`Latency_Tests/`](Latency_Tests/) contains a thread-safe `PerformanceMonitor` (p50/p95/p99,
throughput, CPU and RSS via `psutil`) and a `cProfile` wrapper, plus documented `py-spy` and
`scalene` invocations; `flamegraph.svg` is a captured py-spy profile. These currently profile a
synthetic workload rather than instrumenting the live pipeline — see *Limitations*.

---

## Testing

[`tests/`](tests/) holds three executable harnesses, all driven by generated data with no network
or database dependency:

- `demo_trade_lifecycle.py` — a 4-tick simulator that recomputes `Q*` through an independent
  shadow implementation and compares it against the engine, covering normal sizing, the 60-second
  throttle and the volume cap.
- `integration_test.py` — synthetic history plus 120 ticks through the full in-memory path: bar
  aggregation → strategy → sizing → execution → mark-to-market → reporting.
- `test_strat.py` — signal generation on synthetic bars, and the per-period PnL decomposition.

Run with `PYTHONPATH=. python tests/<file>.py`.

---

## Scope and limitations

Stated explicitly, because they bound what the numbers above mean.

**Model**
- Paper trading against top of book. Fills are assumed at the quoted price adjusted by the cost
  model; there is no queue position, no partial-fill simulation and no rejection handling.
- The market-impact coefficient is fixed, not calibrated.
- Position tracking is a single scalar quantity per asset. There is no cost-basis or FIFO lot
  tracking, so **realised PnL per trade is not computed** — reported PnL is mark-to-market on
  total equity.

**Data and reporting**
- `/api/pnl` returns total mark-to-market return for all five period keys. Correct daily /
  monthly / QTD / YTD decomposition needs an equity-snapshot table that does not exist yet; the
  period arithmetic itself is implemented and tested in `PortfolioManager.calculate_pnl_metrics`.
- Ingestion is append-only: there are no unique constraints and no upserts, so restarting the
  ingestor re-downloads and re-inserts overlapping history.
- Monotonicity validation currently compares locally-stamped receive times. Binance `@bookTicker`
  carries no event time — ordering must be keyed on the `u` update-id, which is not yet read.
- `stop.sh` truncates `candles` and `trades` on shutdown. Comment those lines out to keep history.
- API endpoints expose only a `limit` parameter; strategy and date filtering happen client-side
  over the fetched window, and trades are not yet tagged with the strategy that produced them.

**Infrastructure**
- `apps/persister.py` and the Redis Streams consumer-group path are implemented but not wired
  into the ingestor, which uses an in-process `asyncio.Queue`. The tick table is consequently not
  populated by the default run.
- The `asyncio.Queue` is unbounded and per-tick work is dispatched as fire-and-forget tasks: there
  is no backpressure, no drop policy and no load shedding under a burst.
- No caching layer and no TTL on Redis keys; engine state persists after the producer stops.
- Historical REST download is synchronous and runs on the event loop.
- No CI pipeline. `ruff` and `mypy` are available but run manually and are unconfigured; the test
  harnesses print results rather than asserting, so they cannot gate a build.
- Sphinx is configured but `docs/source/modulos.rst` references module paths that no longer
  exist, so generated API documentation is currently empty.
- `terraform/main.tf` provisions a single EC2 node for demonstration. It opens 5432 to
  `0.0.0.0/0` and the compose file ships default credentials — **not deployable as-is**.

**Scale.** The universe is 10 symbols. Moving to ~300 would break on three axes: Binance's
per-connection stream limit forces connection sharding; per-symbol engine state and unbounded
equity curves grow linearly in memory; and single-writer Postgres inserts become the throughput
ceiling. The intended path is partitioning by symbol hash across replicas over Redis consumer
groups, which the bus already supports — the domain layer would not need to change.
