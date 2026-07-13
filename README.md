# CipherChase — Distributed Cops-and-Robbers over a Peer-to-Peer Network

> Final Project · Course 203.3763 "Orchestration of AI Agents" · University of Haifa · Spring 2026 · Dr. Yoram Segal
> Team `uoh-sqak` — Salah Qadah (323039974) + Andalus Kalash (211435797)

Two mutually-distrustful autonomous agents — a **Cop** and a **Thief** — chase on a 7×7 grid over a
**peer-to-peer FastMCP** network with **no central judge**. Fairness is enforced cryptographically
(**Commit-Reveal + SHA-256 + mutual audit**); the move brain is **pure-Python** (the LLM only writes bluff text).

**Status:** under construction — see `docs/` for the full PRD, PLAN (C4 + ADRs), per-mechanism PRDs, and the TODO.
The academic report, run instructions, and GUI/Replay screenshots will be completed here.

Paired repository (role-swapped): _link added at publish (`uoh-sqak-cop` ⇄ `uoh-sqak-thief`)._
