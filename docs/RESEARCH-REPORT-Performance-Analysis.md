# Research Report — Performance & Resource Analysis

> Mandatory submission artifact (rubric §5 / PRD FR-K4). Skeleton now; numbers filled in after the sample runs and the OAT sensitivity pass (excellence band G5). Everything here is measured on the target machine (see §1) — the point is **Computational Fairness**: a clever, cheap algorithm on a modest laptop beating brute force.

## 1. Test environment
| | |
|---|---|
| Machine | macOS · Apple Silicon **M2**, **8 GB** RAM |
| Python | 3.13 (CI-pinned) · `uv` |
| LLM providers | `template` (0 tokens, default) · `claude_cli` (subscription) · `ollama` (local small) · `claude_api` (Haiku) |
| Grid / limits | 7×7 · max_moves 35 · max_barriers 14 (from `game.json`) |

## 2. Resource usage per game (to measure)
| Metric | template | claude_cli | ollama | claude_api |
|---|---|---|---|---|
| Wall-clock / sub-game | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Peak RSS (MB) | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| CPU % (avg) | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Move-decision latency (ms, p50/p95) | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

*Movement is pure Python and identical across providers — the provider only affects the (optional, throttled) bluff-text layer.*

## 3. Token & cost analysis (to measure)
| Provider | Tokens / hint | Hints / game (`every_n_steps`) | Tokens / game | Tokens / series | $ / series |
|---|---|---|---|---|---|
| template | **0** | n/a | **0** | **0** | **$0** |
| claude_cli | _TBD_ | _TBD_ | _TBD_ | _TBD_ | subscription |
| ollama | 0 (local) | _TBD_ | 0 | 0 | electricity |
| claude_api (Haiku) | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

- Series token budget cap: ~200k (`network_and_league.token_budget_per_series`). A full series at `provider=template` = **0 tokens** — demonstrably within budget.
- RPM under the Gatekeeper token bucket: 30 req/min, 2 concurrent (config `rate_limiter_gatekeeper`).

## 4. Fallback & degradation analysis
- **LLM unavailable / times out** → provider returns a template hint; the **move is never blocked** (FR-D4). Measure: fallback rate, added latency.
- **Gatekeeper 429 / rate-limit** → exponential backoff (5 s) + 3 retries + FIFO queue (depth 100), never drop (NFR-5). Measure: queue occupancy under burst.
- **Silent opponent / tunnel drop** → Deadline Tracker + Watchdog → `TECHNICAL_LOSS` (0/0), never a hang (FR-H3). Measure: detection time vs `turn_timeout`.

## 5. Strategy performance (to measure)
- Heuristic baseline: capture rate as cop / survival rate as thief vs the reference "nearest-edge" brain and vs a random brain (N sub-games, fixed seeds).
- Belief-map accuracy: mean localization error (Manhattan distance from `most_likely()` to true cell) over a game.
- Barrier efficiency: reduction in thief reachable-set per barrier placed.
- *(Excellence)* Expectimax vs heuristic head-to-head; Q-learning **learning curves** (reward vs episodes) if the RL extension ships.

## 6. Sensitivity analysis (OAT — excellence band)
One-at-a-time sweeps over: `smell_trust`, decay ρ, barrier weight λ, belief diffusion α, `lie_probability`, `every_n_steps`. Report each parameter's effect on win-rate and cost. Companion notebook: `analysis/` (Jupyter/LaTeX).

## 7. ISO/IEC 25010 mapping (excellence band)
Brief mapping of the design to functional-suitability, performance-efficiency, reliability, security (zero-trust crypto), maintainability (≤150 modules, SDK layer), portability (uv, config-driven). _TBD table._

## 8. Conclusions
_TBD after runs — expected thesis: the zero-token heuristic on an 8 GB M2 achieves competitive play at $0 and sub-second decisions, satisfying Computational Fairness without cloud/brute-force._
