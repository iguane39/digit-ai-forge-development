# Digit-AI SaaS Forge

**English** · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português](README.pt.md)

> **From idea to a production-ready SaaS, in one command — under a dual code & design gate.**

Digit-AI SaaS Forge is an agentic SaaS accelerator. A **thin orchestration layer**
(`conductor/`) sequences and constrains battle-tested third-party engines to carry a
product intention all the way to a structured, tested, on-brand SaaS repository — without
ever rewriting or forking those engines.

The forge does not reinvent planning, scaffolding, autonomous development, or design
linting. It **conducts** them.

## How it works — a 5-stage chain

| Stage | Name | Role |
|-------|------|------|
| **A** | Scoping | Turn an idea + constraints into a mission config (target, SaaS scope, brand) |
| **B** | Scaffold-first | Generate the production skeleton **before any agent runs** |
| **C** | BMAD bridge | Run agile planning → PRD, architecture, epics, stories — *gated by HITL 1* |
| **D** | Sprint adapter | Place the backlog where the autonomous engine expects it |
| **E** | Supervisor | Run the autonomous sprint under the dual gate — *gated by HITL 2* |

Two structural principles:

- **Scaffold-first** — the production skeleton exists before agents write a line of code.
- **Dual gate** — no story merges unless **both** the code CI (ruff, mypy, pytest,
  Playwright) **and** the design lint (WCAG 2.2 AA, broken refs, on-system) pass.

Two human checkpoints (HITL): PRD & architecture approval, then final review & merge.
Autonomous merging is disabled by design.

## Orchestrated engines (pinned & vendored, never forked)

| Engine | Layer |
|--------|-------|
| [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | Agile planning (brief → PRD → stories) |
| [bmad-autonomous-development](https://github.com/stephenleo/bmad-autonomous-development) | Autonomous sprint execution (one git worktree per story) |
| [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | Deterministic production target (FastAPI + React + PostgreSQL) |
| [@google/design.md](https://github.com/google-labs-code/design.md) | Design-system lint (the design gate) |

## Repository layout

| Path | Contents |
|------|----------|
| [`digitai-saas-forge/`](digitai-saas-forge/) | The code: `conductor/` (master framework), parameterizable target, gates, CI |
| [`docs/`](docs/) | Design corpus: analysis, PRD (BMAD format), architecture, implementation plan, spike notes, execution decisions |
| [`input/`](input/) | The original founder dossier |

## Quickstart

```bash
cd digitai-saas-forge
uv sync
uv run pytest        # code gate (ruff + strict mypy + pytest)
conductor --version
```

## Status

- **Epic 0 — Bootstrap** ✅ merged. Typed `conductor/` skeleton, `A→E` contracts, dual-gate CI, BAD vendoring `@v1.2.0`, dogfooding seed.
- **Epic 1 — Scaffold-first** ✅ merged. Scoping (A) + scaffold (B) + 11-brick catalog + code gate.
- **Epic 2 — Design axis** ✅ merged. Blocking design gate (`@google/design.md@0.3.0` + severity policy), reference `DESIGN.md`, vendored style, token export.
- **Epic 3 — Full loop** ✅ merged. BMAD bridge (C) + HITL 1, sprint adapter (D), supervisor (E) invoking `/bad` with per-story design gate, 3-retry remediation, and HITL 2 — autonomous merge locked off.

All four epics are integrated; both gates are green on GitHub Actions. The full `A→E` chain is wired and tested; running real BMAD/`/bad` requires a Claude Code harness. See [`docs/plan-implementation.md`](docs/plan-implementation.md).

## Running a build — methodology

The run is orchestrated but **governed**: it stops at two human checkpoints by design and never
auto-merges. Attach a specs/constraints dossier; the operator splits scope from constraints,
then drives the chain:

1. **Classify** the attachments — scope (the *what*) vs constraints (the *how*).
2. **Preflight** — `gh` auth + token, `uv`/`node`, network, clone the forge.
3. **Scoping (A)** — derive a `MissionConfig` (11-brick build/buy, t0 forced), then confirm.
4. **Scaffold-first (B)** — generate the skeleton before any agent.
5. **BMAD planning (C) → HITL 1** — PRD/architecture/epics; human approval required.
6. **Sprint config (D)** — backlog layout + `bad:` config (`auto_pr_merge=false`).
7. **Supervised sprint (E) → HITL 2** — `/bad` per story, dual gate, 3-retry remediation; no merge without human review.

Full operator prompt: **[`docs/conductor-run-playbook.md`](docs/conductor-run-playbook.md)**.

## License

[MIT](LICENSE) © 2026 Digit-AI.

---
*Digit-AI · AI consulting & strategy · SaaS accelerator · 2026*
