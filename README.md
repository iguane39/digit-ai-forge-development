# Digit-AI SaaS Forge

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

**Epic 0 (Bootstrap) — delivered & verified.** Typed `conductor/` skeleton, `A→E`
pipeline contracts, dual-gate CI, BAD vendoring `@v1.2.0`, dogfooding seed. Code gate is
green on GitHub Actions. Next: Epic 1 (scaffold-first), Epic 2 (design axis), Epic 3
(full loop) — see [`docs/plan-implementation.md`](docs/plan-implementation.md).

## License

[MIT](LICENSE) © 2026 Digit-AI.

---
*Digit-AI · AI consulting & strategy · SaaS accelerator · 2026*
