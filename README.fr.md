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

- **Epic 0 — Bootstrap** ✅ mergé. Squelette `conductor/` typé, contrats `A→E`, CI double-gate, vendoring BAD `@v1.2.0`, amorçage dogfooding.
- **Epic 1 — Scaffold-first** ✅ mergé. Cadrage (A) + scaffold (B) + catalogue 11 briques + gate code.
- **Epic 2 — Axe design** ✅ mergé. Gate design bloquant (`@google/design.md@0.3.0` + politique de sévérité), `DESIGN.md`, style vendorisé, export de tokens.
- **Epic 3 — Boucle complète** ✅ mergé. Pont BMAD (C) + HITL 1, adapter de sprint (D), superviseur (E) invoquant `/bad` avec gate design par story, remédiation 3 retries et HITL 2 — merge automatique verrouillé.

Les quatre epics sont intégrés ; les deux gates sont verts sur GitHub Actions. La chaîne `A→E` est câblée et testée ; l'exécution réelle de BMAD/`/bad` requiert un harness Claude Code. Voir [`docs/plan-implementation.md`](docs/plan-implementation.md).

## Licence

[MIT](LICENSE) © 2026 Digit-AI.

---
*Digit-AI · Conseil et stratégie IA · accélérateur SaaS · 2026*
