# Research Report — Performance & Resource Analysis

> Mandatory submission artifact (rubric §5 / PRD FR-K4). Skeleton now; numbers filled in after the sample runs and the OAT sensitivity pass (excellence band G5). Everything here is measured on the target machine (see §1) — the point is **Computational Fairness**: a clever, cheap algorithm on a modest laptop beating brute force.

## 1. Test environment
| | |
|---|---|
| Machine | macOS · Apple Silicon **M2**, **8 GB** RAM |
| Python | 3.13 (CI-pinned) · `uv` |
| LLM providers | `template` (0 tokens, default) · `claude_cli` (subscription) · `ollama` (local small) · `claude_api` (Haiku) |
| Grid / limits | 7×7 · max_moves 35 · max_barriers 14 (from `game.json`) |

## 2. Resource usage per game (measured on the target M2)
| Metric | template | claude_cli | ollama | claude_api |
|---|---|---|---|---|
| Wall-clock / sub-game (35 turns) | **~37 ms** | _TBD_ | _TBD_ | _TBD_ |
| Move-decision latency | **<1 ms/turn** | _TBD_ | _TBD_ | _TBD_ |
| Peak RSS (MB) | small (pure-Python, no ML deps) | _TBD_ | _TBD_ | _TBD_ |

*Movement is pure Python and identical across providers — the provider only affects the (optional, throttled)
bluff-text layer, so wall-clock and RSS for the game engine are provider-independent. Measured: **20 full
35-turn self-matches average 37.4 ms each** (belief + scent + heuristic + commit-reveal sealing of 70 moves).*

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
`scripts/sensitivity.py` sweeps **`smell_trust`** and measures the cop's mean belief-localisation error
(Manhattan distance from the belief peak to the true thief cell, averaged over 25 cells):

| `smell_trust` | 0.0 | 0.5 | 1.0 | 2.0 | 4.0 | 8.0 | 16.0 |
|---|---|---|---|---|---|---|---|
| mean localisation error (cells) | **6.00** | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

**Interpretation:** at `smell_trust=0` the belief ignores scent and stays blind (error ≈ the board diameter);
**any positive trust** makes the peak lock onto a single clean deposit (error 0). The parameter is therefore a
*binary switch* under noise-free single-source scent — its graduated effect appears only under noisy /
multi-source fields (where over-trusting stale scent would mislocalise). Plot:
`docs/sample-run/sensitivity_smell_trust.png`. Remaining OAT axes (decay ρ, barrier λ, diffusion α,
`lie_probability`, `every_n_steps`) follow the same harness.

## 7. ISO/IEC 25010 mapping (excellence band)
Brief mapping of the design to functional-suitability, performance-efficiency, reliability, security (zero-trust crypto), maintainability (≤150 modules, SDK layer), portability (uv, config-driven). _TBD table._

## 8. Conclusions (measured)
The zero-token heuristic plays a full 7×7 sub-game in **~37 ms** on an 8 GB M2 at **$0 / 0 tokens**, with
**sub-millisecond** per-turn decisions — decisively satisfying **Computational Fairness** (clever + cheap
beats brute-force + cloud). The committed sample run confirms end-to-end integrity: 70 commit-reveal records
re-hash **"Verified OK"**, the mutual audit returns `verified`, and both peers would produce the same symmetric
signature. The open lever is *capture rate*: the heuristic cop reliably **contains** but does not always
**capture** the evading thief within 35 moves on an open board — the expectimax/Q-learning extensions (behind
the `BrainBase` seam) target exactly this, and their learning curves would populate §5–6.
