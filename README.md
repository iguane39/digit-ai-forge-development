# Digit-AI SaaS Forge — dépôt fondateur

Accélérateur SaaS agentique : mener une idée jusqu'à un produit SaaS de production via
une **couche d'orchestration mince** qui séquence des moteurs tiers (BMAD-METHOD, BAD,
full-stack-fastapi-template, design.md) sous **double gate code & design** et **2 points HITL**.

## Structure du dépôt

| Dossier | Contenu |
|---|---|
| [`digitai-saas-forge/`](digitai-saas-forge/) | **Le code** — squelette du framework maître (`conductor/`), cible paramétrable, gates, CI. Voir son [README](digitai-saas-forge/README.md). |
| [`docs/`](docs/) | **La conception** — analyse, PRD (BMAD), architecture, plan d'implémentation, notes de spike (S-1→S-3), décisions d'exécution. |
| [`input/`](input/) | Le dossier fondateur d'origine (HTML) et ses 6 sources embarquées. |

## Démarrer
```bash
cd digitai-saas-forge
uv sync
uv run pytest    # gate code
```

## État
**Epic 0 (Bootstrap) livré et vérifié** : squelette `conductor/`, contrats typés, double-gate
CI, vendoring BAD `@v1.2.0`, amorçage dogfooding. Gate code vert (ruff + mypy strict + pytest).
Suite : Epic 1 (scaffold-first), Epic 2 (axe design), Epic 3 (boucle complète) — cf.
[`docs/plan-implementation.md`](docs/plan-implementation.md).

---
*Digit-AI · Conseil et stratégie IA · accélérateur SaaS · 2026*
