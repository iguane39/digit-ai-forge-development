# digit-ai-forge-development

> **Idée → SaaS de production PR-ready, en une commande, sous double gouvernance code & design.**

Couche d'orchestration **mince** (`conductor/`) qui séquence des moteurs tiers éprouvés
— elle ne réécrit ni ne forke aucun d'eux (décision canonique 01).

## Quickstart
```bash
uv sync
conductor run "<votre idée de SaaS>"
```

## Le système — chaîne en 5 étapes
`A` Cadrage → `B` Scaffold-first → `C` Pont BMAD *(HITL 1)* → `D` Adapter de sprint → `E` Superviseur `/bad` + double gate *(HITL 2)*

Deux principes : **scaffold-first** (le squelette de prod existe avant tout agent) et
**double gate** (aucun merge si la CI code OU le lint design échoue).

## Décisions canoniques (constitution — non rediscutées)
Voir [`../docs/analyse.md`](../docs/analyse.md) §5. En bref : maître mince · scaffold-first ·
double gate · style injecté au dev · multi-tenancy/RBAC/auth-SSO à t0 · dépendances
épinglées & vendorisées · 2 points HITL · cible & charte paramétrables.

## Forker pour un nouveau SaaS
Paramétrer la cible via [`targets/fastapi-saas/copier.yml`](targets/fastapi-saas/copier.yml)
et la charte via [`design/DESIGN.md`](design/DESIGN.md) (lintable → tokens Tailwind).

## Dépendances épinglées & vendorisées
- `vendor/bad/` — skill **bmad-autonomous-development @ v1.2.0** (cf. [`vendor/bad/README.md`](vendor/bad/README.md))
- `design/design.md.lock` — **@google/design.md @ 0.3.0**
- `design/styles/` — styles awesome-design-skills **copiés** (DE-2, pas de CLI)

## Gouvernance — deux points HITL
1. Validation du PRD & de l'architecture (après l'étape C).
2. Revue & merge final (après le double gate). `auto_pr_merge` est forcé à `false`.

## Double gate en CI
[`../.github/workflows/double-gate.yml`](../.github/workflows/double-gate.yml) — le merge est
bloqué si le job `code` (ruff/mypy/pytest) ou `design` (design.md lint + politique de
sévérité) échoue. Les **deux gates sont bloquants** depuis l'Epic 2. ⚠ Le gate design ne se
fie pas à l'exit code du linter (cf. piège S-2.3) : il parse le JSON et applique sa propre
politique de sévérité.

### Avant de pousser — rejouer le job `code` en local (TF-1072, TF-1101)
Le job `code` a tourné rouge cinq jours sur la branche principale (Ruff E501, plafond 100,
`[tool.ruff] line-length = 100`) sans qu'aucune recette locale ne le montre avant le push.
```bash
uv run python -m conductor.recette_locale
```
Rejoue, dans le même ordre et avec la même configuration que
[`../.github/workflows/double-gate.yml`](../.github/workflows/double-gate.yml), les cinq
étapes du job `code` (ruff, mypy, pytest, ai-antipatterns, porte-neutralisee) — **chacune
indépendamment des autres** : un échec n'arrête jamais les suivantes (TF-1101, cf.
`conductor/recette_locale.py`). Le récapitulatif final NOMME chaque étape rouge, pas
seulement la première rencontrée :
```
recette locale : 4/5 etape(s) verte(s) — echec(s) : ruff
  [ECHEC] ruff
  [OK   ] mypy
  [OK   ] pytest
  [OK   ] ai-antipatterns
  [OK   ] porte-neutralisee
```
Exit 1 si au moins une étape est rouge (bloque le push), 0 si les cinq sont vertes. Les
commandes peuvent aussi se rejouer une par une (même configuration) :
```bash
uv run ruff check .
uv run mypy
uv run python -m pytest
uv run python -m conductor.gates.ai_antipatterns_gate conductor pyproject.toml
uv run python -m conductor.gates.porte_neutralisee_gate ..
```

## Documentation de conception
[`../docs/`](../docs/) — analyse, PRD, architecture, plan d'implémentation, notes de spike,
décisions d'exécution.

---
*Digit-AI · Conseil et stratégie IA · accélérateur SaaS · 2026*
