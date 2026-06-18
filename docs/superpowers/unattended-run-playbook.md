# Unattended Run — Playbook gouverné (workflow EPIC)

> Procédure pour piloter un run multi-EPIC « lance et reviens » de la forge/des projets, via le
> workflow EPIC superpowers (brainstorm → spec → plan → exécution subagent-driven → revue → merge
> → récap). Objectif : **débit non supervisé maximal SANS affaiblir la gouvernance**.
> Templates associés : `templates/PLAN.md`, `templates/DECISIONS.md`.

## Principe directeur — frontière cérémonie / gouvernance
On supprime la cérémonie, on garde la gouvernance. Listes indépendantes (pas de correspondance
ligne à ligne).

| PRÉSERVÉ (jamais contourné) | SUPPRIMÉ / batché |
|---|---|
| Double gate (ruff/mypy/pytest + design WCAG) | Validation de design par EPIC |
| Non-régression | « Relis la spec » par EPIC |
| 2 HITL produit (uniquement si `conductor run`) | « Démarrer l'EPIC suivante ? » |
| Revue humaine avant merge vers `main`/cible partagée | Choix du mode d'exécution |
| `auto_pr_merge=false` | Messages d'avancement bloquants |

**Distinction de merge.** Merge LOCAL par EPIC (branche de run, gardé par double gate +
non-régression) = mécanisme d'enchaînement réversible → **autonome**. Merge FINAL vers `main`
(push/PR, irréversible) → **humain (revue finale)**. « Merge automatique » signifie TOUJOURS local.

## Cycle de vie — 2 gates humains

### Phase −1 — Configuration de départ (reflet de `select_onramp`, automatique)
Avant le macro-brainstorm, déterminer la **configuration de travail**. Le routage est déjà
implémenté par `conductor/onramp/select_onramp` (détection stack + distance) — ne rien concevoir,
juste choisir `--mode` (+ `--repo`/`--intent` en brownfield) :

1. **From scratch** → `greenfield` (`ScaffoldOnramp`) : génère le squelette, `PLAN.md` de zéro.
2. **Continuation méthodo** → `brownfield`, repo déjà conforme (`NoOnramp`, distance A : pyproject
   + DESIGN.md + CI présents) : **pas de scaffold** ; la **baseline** est capturée et alimente la
   non-régression ; ne (re)brainstormer que les **EPICs nouvelles** ; reprendre la numérotation des
   tags à `run/<slug>/epic-<n+1>`.
3. **Externe** → `brownfield`, repo à normaliser (`AdapterOnramp` distance C / `BuilderOnramp`
   stack non-FastAPI) + **HITL-0** si dégradation déclarée, puis `intent` remediation / complement
   / both.

Toutes les bretelles produisent le même `Substrate` → **le reste du lifecycle (Phases 0-2, 2 gates,
GATE 2 A/B/C, politiques) est identique pour les 3 configurations.**

### Phase 0 — Plan & pré-vol  ⛔ GATE 1 (humain, unique)
1. Macro-brainstorm → liste des EPICs → instancier `PLAN.md` (tous `todo`, déps, ordre, budget,
   `max_parallel`, branche `run/<slug>`).
2. Scanner TOUTES les EPICs → extraire les décisions fonctionnelles/techniques anticipables.
3. Poser UN questionnaire groupé (chaque choix = recommandation par défaut + « tout accepter »),
   y compris le **choix de la politique de merge GATE 2** (ci-dessous). Consigner dans `DECISIONS.md`.
4. Estimer budget/temps ; si gros périmètre, proposer un **slice MVP d'abord** puis extension.
5. Obtenir le consentement unique « GO unattended ». Créer la branche `run/<slug>`.

### Phase 1 — Boucle autonome  (aucun arrêt humain hors politiques ci-dessous)
Pour chaque EPIC (ordre des déps ; EPICs indépendantes en parallèle dans la limite `max_parallel`) :
brainstorm → spec (auto-validée, consulte `DECISIONS.md`) → plan → exécution subagent-driven →
double gate + non-régression → merge LOCAL si vert (+ tag) → maj `PLAN.md` + `RUN_LOG.md` →
récap+KPIs (non bloquant) → démarrage automatique de l'EPIC suivante.

### Phase 2 — Revue finale  ⛔ GATE 2 (humain, unique)
Présenter un récap PAR EPIC adossé aux tags (titre, KPIs, décisions par défaut, diff résumé),
les EPICs `blocked`, les questions ouvertes, le coût/temps vs budget. Demander la validation
explicite pour merger la branche de run sur `main`. RIEN n'est mergé sur `main` avant ce feu vert.

## Politiques d'exécution autonome (Phase 1)

### Défaut-sinon-stop (décisions émergentes)
- **Anticipable** → déjà tranchée au pré-vol (zéro interruption).
- **Émergente non bloquante** → appliquer le défaut le plus raisonnable, le consigner dans
  `DECISIONS.md` (hypothèse + justification), continuer.
- **Irréversible / destructive / sécurité-conformité / hors-mandat / contournement d'un
  garde-fou** → NE PAS deviner. Marquer l'EPIC `blocked`, poursuivre les indépendantes, surfacer
  à la revue finale.

### Échec & résilience
- Double gate rouge → jusqu'à 3 retries → sinon EPIC `blocked` + poursuite des indépendantes.
- Reprise idempotente : `PLAN.md` (statuts) = checkpoint ; redémarrer à la 1ʳᵉ EPIC non `done`,
  sans refaire le `done` ni retaguer.
- Budget : plafond temps/coût + `max_parallel` (`PLAN.md`) ; arrêt propre au seuil, récap reprenable.
- Avancement asynchrone : jamais de message bloquant ; `PLAN.md` + `RUN_LOG.md` à jour ; UNE
  notification aux seuls jalons (GATE 1/2, `blocked`, fin de run).

## GATE 2 — politique de merge (choix posé au pré-vol)
Avant la 1ʳᵉ EPIC, poser UNE question (recommandation en tête) et expliquer l'impact CHIFFRÉ :

> « Veux-tu revoir chaque EPIC avant son intégration, ou laisser le run intégrer en autonomie
> et tout revoir à la fin ? »
> - **A. Auto-intégration (recommandé)** — chaque EPIC verte est mergée automatiquement sur la
>   branche de run, sans arrêt ; tu es seulement informé, la suivante démarre. ~0 arrêt → débit max.
> - **B. Revue avant chaque merge** — arrêt avant chaque intégration. N arrêts pour N EPICs →
>   contrôle max, run nettement plus long.
> - **C. Revue des EPICs risquées seulement** — auto par défaut, arrêt pour les EPICs marquées
>   « sensibles » au pré-vol (migrations, sécurité, irréversible).

**Invariants — quel que soit le choix (jamais contournés) :**
- Merges automatiques = LOCAUX, toujours sur la branche de run, JAMAIS vers `main` ni PR auto.
  `auto_pr_merge` reste `false`.
- Merge+tag d'une EPIC UNIQUEMENT si double gate + non-régression VERTS. EPIC `blocked` : ni
  mergée ni taguée, surfacée à la revue finale.
- Après intégration réussie : tag `run/<slug>/epic-<n>` (immutable ; pas de retag à la reprise)
  + entrée `RUN_LOG.md`.
- Revue (B/C) qui rejette une EPIC → la rouvrir avec feedback (retry borné à 3), sinon `blocked` ;
  le run poursuit les indépendantes.
- EPICs parallèles → worktrees réintégrés SÉQUENTIELLEMENT sur la branche de run, non-régression
  évaluée à chaque intégration.

## Gabarit `RUN_LOG.md` (à instancier par run, append-only)
```
# RUN_LOG — Run <slug>
[HH:MM] GATE 1 · GO unattended · politique merge=<A|B|C> · <n> EPICs · budget=<…>
[HH:MM] EPIC <n> · spec · auto-validée
[HH:MM] EPIC <n> · gate · code ✅ design ✅ régression ✅
[HH:MM] EPIC <n> · merge+tag · run/<slug>/epic-<n>
[HH:MM] EPIC <n> · décision · défaut « <x> » appliqué (voir DECISIONS.md)
[HH:MM] EPIC <n> · blocked · <raison> → revue finale
[HH:MM] notification · <jalon>
[HH:MM] GATE 2 · revue finale présentée · attente validation merge main
```

## Prompt orchestrateur (copier-coller pour lancer un run unattended)
```
Tu pilotes un RUN UNATTENDED GOUVERNÉ du workflow EPIC. Suis ce playbook à la lettre.

PHASE -1 (config de départ, automatique via select_onramp) : déterminer la configuration —
1 from-scratch (greenfield/ScaffoldOnramp) ; 2 continuation méthodo (brownfield repo conforme/
NoOnramp : pas de scaffold, baseline→non-régression, brainstorm des EPICs nouvelles seulement,
tags repris à epic-<n+1>) ; 3 externe (brownfield Adapter/BuilderOnramp + HITL-0 + intent). Le
reste du lifecycle est identique pour les 3.

PHASE 0 (GATE 1) : macro-brainstorm → PLAN.md (EPICs, déps, budget, max_parallel, branche
run/<slug>). Scanne TOUTES les EPICs, extrais les décisions anticipables, pose-les en UN
questionnaire groupé (recommandation par défaut + « tout accepter »), DONT le choix de politique
de merge (A auto / B chaque / C risquées, défaut A) avec impact chiffré. Consigne dans
DECISIONS.md. Estime budget/temps ; gros périmètre → propose un slice MVP. Attends le « GO ».

PHASE 1 (autonome, AUCUN arrêt de cérémonie) : pour chaque EPIC, brainstorm → spec auto-validée
(consulte DECISIONS.md) → plan → exécution subagent-driven → double gate + non-régression →
merge LOCAL sur run/<slug> si vert + tag run/<slug>/epic-<n> → maj PLAN.md + RUN_LOG.md →
récap+KPIs non bloquant → EPIC suivante automatiquement. Décision émergente : défaut-sinon-stop
(non bloquant = défaut + log + continue ; irréversible = blocked + continue les indépendantes).
Gate rouge : 3 retries puis blocked. Informe en ASYNCHRONE (fichiers + notification aux jalons).

PHASE 2 (GATE 2) : récap PAR EPIC (tags), EPICs blocked, questions ouvertes, coût/temps. DEMANDE
la validation pour merger run/<slug> sur main. NE MERGE JAMAIS main sans ce feu vert.

INTERDITS : ne contourne aucun garde-fou ; merge automatique = LOCAL uniquement ; auto_pr_merge
reste false ; ne tague jamais une EPIC blocked ; ne devine pas en silence sur l'irréversible ;
ne supprime pas la traçabilité (PLAN.md + DECISIONS.md + RUN_LOG.md).
```
