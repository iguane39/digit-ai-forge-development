# Runbook pilote B-8 — Mode unattended sur petit périmètre

> Procédure **manuelle** pour éprouver le mode unattended gouverné sur un run réel mais borné
> (2-3 EPICs). Objectif : valider la procédure avant usage réel et révéler les manques (→ B-4, B-5).
> Référence : `docs/superpowers/unattended-run-playbook.md` + templates `docs/superpowers/templates/`.

## Prérequis
1. Un **petit projet réel déjà cadré** (idée + contraintes claires), 2-3 EPICs maximum.
2. Les templates copiés à la racine du run : `PLAN.md`, `DECISIONS.md`, `RUN_LOG.md`, `SPEC_FINDINGS.md`.
3. Branche de run dédiée : `run/<slug>`.

## Procédure (suit le lifecycle du playbook)
1. **Phase −1 — Configuration** : déterminer from-scratch / continuation / externe (routage onramp).
   Pour le pilote : **from-scratch** (greenfield) recommandé — le plus simple à éprouver.
2. **Phase 0 — GATE 1 (pré-vol)** :
   - macro-brainstorm → `PLAN.md` (2-3 EPICs, déps, budget, `max_parallel`, branche `run/<slug>`) ;
   - scan des EPICs → questionnaire de décisions groupé → `DECISIONS.md` ;
   - **politique de merge = A (auto-intégration)** pour éprouver le débit du mode nominal ;
   - donner le « GO unattended ».
3. **Phase 1 — Boucle autonome** : laisser tourner. Observer **sans intervenir** sauf bloqueur dur.
4. **Phase 2 — GATE 2 (revue finale)** : récap par EPIC (tags `run/<slug>/epic-<n>`), décider le merge `main`.

## Grille d'observation (le cœur du pilote)
| Point à mesurer | Attendu | Observé |
|---|---|---|
| Arrêts humains réels | 2 (GATE 1, GATE 2) seulement | |
| Friction résiduelle (questions de cérémonie qui subsistent) | 0 | |
| Exactitude des statuts `PLAN.md` après chaque EPIC | fidèle | |
| Tags `run/<slug>/epic-<n>` posés (gate vert uniquement) | oui | |
| Décisions émergentes : défaut-sinon-stop respecté | oui | |
| `DECISIONS.md` / `RUN_LOG.md` tenus à jour | oui | |
| Notifications aux jalons (cf. B-5) | reçues | |
| EPIC `blocked` correctement surfacée | oui | |
| Reprise possible depuis `PLAN.md` (test : interrompre puis relancer) | oui | |

## Sûreté
- Périmètre **petit** (2-3 EPICs) : ne pas lancer un gros run pour un premier pilote.
- Double gate + non-régression actifs ; `main` jamais mergé sans la revue finale (GATE 2).
- Merges locaux automatiques sur `run/<slug>` uniquement (jamais GitHub sans humain).

## Sortie de B-8
- Friction résiduelle observée → tickets concrets.
- Si la tenue manuelle du `PLAN.md` est pénible → justifie **B-4** (helper conductor).
- Si l'absence/forme des notifications gêne → calibre **B-5** (canal de notification).
- Verdict : le mode « lance et reviens » est-il utilisable en l'état ?
