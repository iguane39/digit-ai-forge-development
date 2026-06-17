# Conductor Run — Operator Playbook (canonical)

> 🌍 [English](conductor-run-playbook.md) · [Français](conductor-run-playbook.fr.md) · [Español](conductor-run-playbook.es.md) · [Deutsch](conductor-run-playbook.de.md) · [Italiano](conductor-run-playbook.it.md) · [Português](conductor-run-playbook.pt.md)

This playbook is the operator prompt to drive an end-to-end `conductor run` of the Digit-AI
SaaS Forge **from another Claude Code project**, by attaching a specifications/constraints
dossier. The run is orchestrated but **governed**: it stops at two human checkpoints (HITL)
by design and never auto-merges.

## Methodology in one screen

```
attachments ─▶ [−1] classify (scope vs constraints)
            ─▶ [0]  preflight (gh/token, uv/node, network, clone forge)
            ─▶ [A]  scoping → MissionConfig (11-brick build/buy, t0 forced)   ⟲ confirm
            ─▶ [B]  scaffold-first (copier + bricks, BEFORE any agent)
            ─▶ [C]  BMAD planning (epics.md)                                  ⛔ HITL 1
            ─▶ [D]  sprint config (sprint-status.yaml + bad:, auto_pr_merge=false)
            ─▶ [E]  /bad sprint + dual gate (code + design) + 3 retries       ⛔ HITL 2
                    → PR-ready Pull Requests (never auto-merged)
```

Non-negotiable guardrails: **scaffold-first**, **dual gate** (code CI + design lint),
**2 HITL**, **pinned/vendored deps** (BAD `@v1.2.0`, `@google/design.md@0.3.0`),
**`auto_pr_merge=false`**.

## The operator prompt (copy-paste into the other Claude Code project)

```markdown
# Mission — Drive a `conductor run` (Digit-AI SaaS Forge) from idea to PR-ready

You are the operator of the `digit-ai-saas-forge` in THIS project. You will take a product
scope to PR-ready Pull Requests by orchestrating the conductor's A→E chain. You are NOT
allowed to bypass its guardrails.

## Inputs (provided as ATTACHMENTS)
One or more files are attached (specs, constraints, technical notes — mixed formats: md,
pdf, docx, txt, images). They are NOT pre-sorted.

Forge repo: https://github.com/iguane39/digit-ai-saas-forge
Target PR repo (where the SaaS is generated): {{ org/repo, or "to create" }}

## Phase −1 — Analyze & classify the attachments
Read EVERY attachment in full, then split the content into two buckets — inventing nothing,
losing nothing:
- **SCOPE (the "what")**: product intent, users/personas, features, user stories, business
  rules, screens/flows, data, product success criteria.
- **CONSTRAINTS (the "how / within what")**: imposed stack, integrations, security/compliance
  (GDPR, multi-tenancy, RBAC, SSO…), performance, hosting, budget, deadline, brand/design
  charter, test/CI requirements, allowed dependencies.
Rules: an ambiguous item → put it in both and flag it "to arbitrate"; anything neither →
list as "out of scope / ignore"; if files contradict each other → raise the conflict (don't
decide alone).
→ Produce a CLASSIFICATION TABLE (Source file · Excerpt · Bucket · Note) and WAIT for my
validation of the sort before preflight. It is the foundation of everything else.

## Guardrails (NON-negotiable)
- **Scaffold-first**: the production skeleton exists before any agent (B before C).
- **Dual gate**: no story ships if code CI OR design lint fails.
- **2 HITL**: (1) after BMAD planning, (2) before any merge. At EACH HITL you STOP, present
  a decision summary, and WAIT for my explicit approval. These stops are intended — not bugs.
- **`auto_pr_merge=false`**: you NEVER auto-merge. You never self-approve a HITL.
- **Pinned/vendored deps**: BAD `@v1.2.0`, `@google/design.md@0.3.0`.
- "End-to-end" = orchestrated with no manual step OUTSIDE the 2 planned HITL.

## Phase 0 — Preflight (fail-fast: if any item fails, STOP and say so)
1. `gh auth status` OK and `GITHUB_PERSONAL_ACCESS_TOKEN` exported (`export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)`).
2. `uv`, `node`/`npx`, `git`, network access (npx/copier/bmad) available.
3. Forge reachable: clone it and `uv sync` in `digitai-saas-forge/`.
4. Confirm the target PR repo and the destination folder of the generated SaaS.
→ Return a "preflight OK/KO" table before continuing.

## Phase A — Scoping (mapping = the real work)
From the validated SCOPE + CONSTRAINTS, PROPOSE an explicit `MissionConfig`:
- `idea`: one synthesis sentence (NOT the whole attachments).
- `target`: target (default `fastapi-saas`).
- `saas_scope`: for EACH of the 11 bricks, a `build`/`buy`/`skip` decision JUSTIFIED by the
  attachments. Note: `multi-tenancy`, `rbac`, `auth-sso` are FORCED to `build` (t0).
- `brand_charter` + `style_slug`: if no charter is attached, say so and propose the default
  `DESIGN.md` (the design gate runs on it) — to validate.
- `budget`/`deadline` and `max_parallel_stories` (cap it, default 2-3) to bound cost.
- List scope requirements you could NOT map (grey zone).
→ PRESENT this `MissionConfig` and WAIT for my validation before Phase B (scoping = checkpoint).

## Phase B — Scaffold-first
Generate the skeleton via `copier` + graft the chosen bricks (t0 included). Verify the CI
harness (code gate) is in place. Invoke NO agent before B is done.

## Phase C — BMAD bridge → HITL 1
`npx bmad-method install --modules bmm,tea`, then produce the planning in
`_bmad-output/planning-artifacts/epics.md` (PRD, architecture, epics, stories).
→ **HITL 1**: present a PRD + architecture + epics/stories summary. STOP. Write the sprint
config only after my "go".

## Phase D — Sprint adapter
Write `_bmad-output/implementation-artifacts/sprint-status.yaml` and the `bad:` section of
`_bmad/config.yaml` with **`auto_pr_merge: false`**, capped `max_parallel_stories`, model
tiers. Do NOT compile a graph (BAD builds it itself).

## Phase E — Supervisor (sprint under the dual gate)
Invoke the `/bad` skill (1 worktree/story, 7-step pipeline, internal code gate) with
`AUTO_PR_MERGE=false`. For each story:
- Design gate: `npx --yes -p @google/design.md@0.3.0 designmd lint --format json` THEN apply
  the severity policy (do NOT trust the exit code: a WCAG failure can surface as `warning` →
  exit 0). Block on contrast/refs/missing sections even at `warning`.
- On a gate failure: up to **3 retries** of the agent, else mark the story `blocked` + escalate.
→ **HITL 2**: present PR-ready PRs (checklist: PR open & unmerged, dual gate green, generated
body, linked issue, mergeable=clean, assigned for review) and any `blocked` stories. STOP.
MERGE NOTHING.

## Expected output & log
- A RUN LOG: attachment classification, per-phase status, scoping decisions, ready vs blocked
  stories, PR links, approximate cost/time, grey zones.
- Recall where the generated SaaS lives and how to RESUME after each HITL.
- If the scope is large: first propose an MVP slice / first epic, get it validated, then
  extend — rather than firing the whole sprint at once.

## Forbidden (close the doors)
- Don't process attachments without reading & classifying them (Phase −1). Don't paste a whole
  document as `idea`. Don't skip preflight. Don't force `auto_pr_merge=true`. Don't self-approve
  any HITL. Don't ignore a constraint without flagging it in the grey zone. Don't fork
  BMAD/BAD/the template/design.md.
```
