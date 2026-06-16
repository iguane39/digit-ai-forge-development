# Backlog d'amorçage — digitai-saas-forge

> Brief d'amorçage du **dogfooding** (DE-1) : BMAD-METHOD re-formalisera ce backlog en
> artefacts versionnés dans `_bmad-output/planning-artifacts/epics.md`.
> Détail et traçabilité : [`../../docs/plan-implementation.md`](../../docs/plan-implementation.md).

## Epic 0 · Bootstrap — gate : CI verte sur repo vide
- 0.1 Squelette `conductor/` + contrats pydantic + `pyproject.toml` (uv)
- 0.2 Vendoring du skill BAD @ v1.2.0
- 0.3 `copier.yml` de la cible fastapi-saas
- 0.4 `double-gate.yml`
- 0.5 Test d'intégration maître (casse au breaking change upstream)
- 0.6 Dogfooding : installer BMAD (`bmm,tea`) + ce brief

## Epic 1 · Scaffold-first SaaS — gate : gate code (pytest + e2e)
- 1.1 `scaffold.py` : `copier copy` + `.env`
- 1.2 Greffe multi-tenancy (`tenant_id` row-level)
- 1.3 Greffe RBAC (Casbin)
- 1.4 Greffe auth/SSO (Authlib)
- 1.5 `cadrage.py` : produit `MissionConfig`
- 1.6 `code_gate.py`

## Epic 2 · Axe design — gate : gate design (WCAG · refs)
- 2.1 Brancher `design.md lint --format json` en CI (@0.3.0)
- 2.2 `design_gate.py` : politique de sévérité sur le JSON
- 2.3 Écrire `DESIGN.md` (charte Digit-AI)
- 2.4 Vendoriser 1 style (copie locale)
- 2.5 Export tokens (css-tailwind / dtcg)

## Epic 3 · Boucle complète — gate : double gate + revue humaine
- 3.1 `bmad_bridge.py` (C) + HITL 1
- 3.2 `sprint_config.py` (D) : layout + config `bad:`
- 3.3 `supervisor.py` (E) : invoque `/bad` + gate design
- 3.4 Remédiation : 3 retries → escalade HITL (DE-3)
- 3.5 HITL 2 + branch protection
- 3.6 CLI `conductor run`
- 3.7 README

## Critères de succès du repo
1. `conductor run "<idée>"` → repo SaaS PR-ready (checklist DE-4)
2. Double gate vert (code + design)
3. Multi-tenant + RBAC + auth/SSO présents
4. 2 points HITL respectés
5. Dépendances épinglées & vendorisées
