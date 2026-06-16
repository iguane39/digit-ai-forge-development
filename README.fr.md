# Digit-AI SaaS Forge

[English](README.md) · **Français** · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português](README.pt.md)

> **De l'idée à un SaaS prêt pour la production, en une commande — sous double gate code & design.**

Digit-AI SaaS Forge est un accélérateur SaaS agentique. Une **couche d'orchestration mince**
(`conductor/`) séquence et contraint des moteurs tiers éprouvés pour mener une intention
produit jusqu'à un dépôt SaaS structuré, testé et conforme à une charte — sans jamais
réécrire ni forker ces moteurs.

La forge ne réinvente ni la planification, ni l'échafaudage, ni le développement autonome,
ni le lint design. Elle les **orchestre**.

## Fonctionnement — une chaîne en 5 étapes

| Étape | Nom | Rôle |
|-------|-----|------|
| **A** | Cadrage | Transformer une idée + des contraintes en config de mission (cible, scope SaaS, charte) |
| **B** | Scaffold-first | Générer le squelette de production **avant tout agent** |
| **C** | Pont BMAD | Lancer la planification agile → PRD, architecture, epics, stories — *gate HITL 1* |
| **D** | Adapter de sprint | Placer le backlog là où le moteur autonome l'attend |
| **E** | Superviseur | Lancer le sprint autonome sous double gate — *gate HITL 2* |

Deux principes structurants :

- **Scaffold-first** — le squelette de production existe avant que les agents écrivent une
  ligne de code.
- **Double gate** — aucune story n'est mergée si la CI code (ruff, mypy, pytest, Playwright)
  **et** le lint design (WCAG 2.2 AA, refs cassées, on-system) ne passent pas tous les deux.

Deux points de validation humaine (HITL) : approbation du PRD & de l'architecture, puis revue
& merge final. Le merge automatique est désactivé par conception.

## Moteurs orchestrés (épinglés & vendorisés, jamais forkés)

| Moteur | Couche |
|--------|--------|
| [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | Planification agile (brief → PRD → stories) |
| [bmad-autonomous-development](https://github.com/stephenleo/bmad-autonomous-development) | Exécution autonome du sprint (un worktree git par story) |
| [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | Cible de production déterministe (FastAPI + React + PostgreSQL) |
| [@google/design.md](https://github.com/google-labs-code/design.md) | Lint du design system (le gate design) |

## Arborescence du dépôt

| Chemin | Contenu |
|--------|---------|
| [`digitai-saas-forge/`](digitai-saas-forge/) | Le code : `conductor/` (framework maître), cible paramétrable, gates, CI |
| [`docs/`](docs/) | Corpus de conception : analyse, PRD (format BMAD), architecture, plan d'implémentation, notes de spike, décisions d'exécution |
| [`input/`](input/) | Le dossier fondateur d'origine |

## Démarrage rapide

```bash
cd digitai-saas-forge
uv sync
uv run pytest        # gate code (ruff + mypy strict + pytest)
conductor --version
```

## Statut

**Epic 0 (Bootstrap) — livré & vérifié.** Squelette `conductor/` typé, contrats du pipeline
`A→E`, CI double-gate, vendoring BAD `@v1.2.0`, amorçage dogfooding. Le gate code est vert
sur GitHub Actions. Suite : Epic 1 (scaffold-first), Epic 2 (axe design), Epic 3 (boucle
complète) — voir [`docs/plan-implementation.md`](docs/plan-implementation.md).

## Licence

[MIT](LICENSE) © 2026 Digit-AI.

---
*Digit-AI · Conseil et stratégie IA · accélérateur SaaS · 2026*
