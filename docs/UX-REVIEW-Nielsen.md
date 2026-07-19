# UX Review — Nielsen's 10 Heuristics on the CipherChase Arena & Replay

> Excellence-band review (rubric §9–16). Conducted against the Masterclass 3D Arena
> (`viz/`, http://localhost:8777) and the Tkinter Replay Viewer. Each heuristic: verdict + what we changed.

| # | Heuristic | Verdict | Evidence / change made |
|---|---|---|---|
| 1 | Visibility of system status | ✅ | Turn counter, play/pause state, gap/barriers/score chips, audit banner, per-chip verdict colors; `aria-live` on status regions |
| 2 | Match between system & real world | ✅ | "Cop/Thief", "Verified OK", "TAMPERED — match void 0/0" — league language, not internals; hashes shown as short `#a1b2c3d4` chips |
| 3 | User control & freedom | ✅ | Scrub anywhere, pause, step ←/→, speed 0.5–2×, orbit override with auto-resume, Honest/Tampered toggle is reversible |
| 4 | Consistency & standards | ✅ | One accent per role everywhere (cyan cop / magenta thief / amber walls) across board, rail, chips, sparkline; standard media-player transport layout |
| 5 | Error prevention | ✅ | Tampered data is a *fixture toggle*, not an editable field; malformed live games fall back to the bundled replay instead of a blank canvas |
| 6 | Recognition over recall | ✅ | On-screen key map (bottom-left), tooltips on view buttons, labeled toggles — no memorized commands needed |
| 7 | Flexibility & efficiency | ✅ | Full keyboard map (space/←→/1-2-3/N/S/Q) for power users; mouse-only path also complete |
| 8 | Aesthetic & minimalist design | ✅ | Single accent family on near-black; HUD reduced to 5 chips + one ticker; bloom tuned down after the first draft read as "chaotic" (user feedback, fixed) |
| 9 | Help users recognize/recover from errors | ✅ | The tamper path *names the consequence* ("match void 0/0") and pinpoints the forged chip in red; replay lists per-step verdicts |
| 10 | Help & documentation | ✅ | README arena section with screenshots; `docs/INTEROP-CONTRACT.md` for opponents; key map in-app |

**Accessibility notes:** `prefers-reduced-motion` disables auto-rotate/pulses/slow-mo; ARIA labels on toolbar,
rail, sparkline; focus-visible outlines; verdicts encode state in **text + shape + color** (never color alone).
**Open items (tracked):** split-screen dual-view (T609) and guided tour (T621) would further serve heuristics 6/10.
