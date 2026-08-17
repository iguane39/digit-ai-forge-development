# Digit-AI Forge Development

**English** · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português](README.pt.md)

> **From idea to a production-ready SaaS, in one command — under a dual code & design gate.**

## Catalogue de services

> Section proposée par la campagne « catalogues » du pilot (2026-08-13) — générée depuis
> la source unique `catalogues/catalogue.jsonl` du pilot (v1.6.0, challengée état de
> l'art le 12/08/2026). **prouvé** = preuve exécutée ; *déclaré* = méthode documentée seulement.

| Service | Intention (« je veux… ») | Point d'entrée | Statut |
|---|---|---|---|
| **Construire le produit sous gates** | transformer mes exigences et mon design en produit qui fonctionne | `méthode du run-playbook appliquée par agent (mode degrade) ; gates rejoués : ruff check + pytest` | prouvé (experimental) |
| **Double gate code + design** | garantir que rien ne passe sans vérification code ET design | `.github\workflows\double-gate.yml + conductor\gates\design_gate.py` | prouvé (production) |
| **Gate spec (under/over-build)** | détecter ce que le code sous-livre ou sur-livre par rapport à la spec | `conductor (gate spec), remédiation bornée à 3` | déclaré (experimental) |
| **Conductor bout en bout (CLI)** | lancer « idée → SaaS » en une commande | `uv run --project <forge> python -m conductor run "<idée>"` | déclaré (experimental) |
| **Générer DESIGN.md linté** | produire le document design du produit accepté par le gate | `generer-design-md.mjs (D-V2 soldée le 07/08)` | prouvé (experimental) |
| **Gate anti-patterns IA** | bloquer imports fantômes, secrets en dur et routes sans auth avant merge | `conductor\gates\ai_antipatterns_gate.py` | prouvé (experimental) |
| **Gate de mutation (3e métrique)** | mesurer la force réelle de mes tests, pas seulement leur couverture | `conductor\gates\mutation_gate.py + job CI mutation` | prouvé (experimental) |

Le catalogue consolidé des dix forges vit chez le pilot :
[digit-ai-factory/catalogues/CATALOGUES.md](https://github.com/iguane39/digit-ai-factory/blob/main/catalogues/CATALOGUES.md).

## 🚀 Start with one sentence

Never installed anything? Open a Claude Code session (or any coding agent) in your project folder — an empty folder for a brand-new project — and paste:

> **Use the Digit-AI Forge Development (https://github.com/iguane39/digit-ai-forge-development) on my current folder to build, continue, or remediate this project — follow its run-playbook `docs/run-playbook.md`.**

That's it. The playbook clones/updates the forge itself, then **auto-detects** the context (new · continuation · external repo) and the Git provider (GitHub or Azure DevOps) with **zero variables to fill**, and proposes what to do before executing. Append *"unattended end to end"* to run the whole backlog without stops (except the human review gate, HITL 2).

Digit-AI Forge Development is an agentic SaaS accelerator. A **thin orchestration layer**
(`conductor/`) sequences and constrains battle-tested third-party engines to carry a
product intention all the way to a structured, tested, on-brand SaaS repository — without
ever rewriting or forking those engines.

The forge does not reinvent planning, scaffolding, autonomous development, or design
linting. It **conducts** them.

## How it works — a 5-stage chain

> 📊 **Visual map:** [interactive process diagram — 6 languages](https://iguane39.github.io/digit-ai-forge-development/forge-process-schema.html?lang=en) (inputs · A→E · gates · HITL · iterative loop).

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
| [`digit-ai-forge-development/`](digit-ai-forge-development/) | The code: `conductor/` (master framework), parameterizable target, gates, CI |
| [`docs/`](docs/) | Design corpus: analysis, PRD (BMAD format), architecture, implementation plan, spike notes, execution decisions |
| [`input/`](input/) | The original founder dossier |

## Quickstart

```bash
cd digit-ai-forge-development
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

**Start here — single entry point:** **[`docs/run-playbook.md`](docs/run-playbook.md)**. It updates the forge, detects your context (new build / continuation / external repo / forge update) and routes to the right flow. Detailed references: [`conductor-run-playbook.md`](docs/conductor-run-playbook.md) (A→E phases) and [`unattended-run-playbook.md`](docs/superpowers/unattended-run-playbook.md) (autonomous "launch & return" mode).

## License

[MIT](LICENSE) © 2026 Digit-AI.

---
*Digit-AI · AI consulting & strategy · SaaS accelerator · 2026*
