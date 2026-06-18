# Design — Mode unattended gouverné (workflow EPIC)

> Date : 2026-06-18 · Statut : **brainstorming validé** (en attente de revue de la spec).
> Portée : artefacts de process (procédure + templates). **Aucun code conductor**, aucun gate à repasser.
> Cible : le **workflow EPIC superpowers** (brainstorm → spec → plan → exécution subagent-driven →
> revue → merge → récap) qui construit la forge et les projets. Pas le pipeline produit A→E.

## 1. Objectif

Maximiser le **débit non supervisé** d'un run multi-EPIC (« lance et reviens »), en supprimant la
**friction de coordination**, SANS affaiblir la **gouvernance**. La douleur visée : sur gros
périmètre, les arrêts fréquents (questions, validations de specs, « démarrer l'EPIC suivante ? »,
messages d'avancement bloquants) rallongent le run.

## 2. Principe directeur — frontière cérémonie / gouvernance

Règle unique : **on supprime la cérémonie, on garde la gouvernance.** Les deux colonnes sont des
listes indépendantes (pas de correspondance ligne à ligne).

| PRÉSERVÉ (jamais contourné) | SUPPRIMÉ / batché |
|---|---|
| Double gate (ruff/mypy/pytest + design WCAG) | Validation de design par EPIC |
| Non-régression | « Relis la spec » par EPIC |
| 2 HITL produit (uniquement si `conductor run`) | « Démarrer l'EPIC suivante ? » |
| Revue humaine avant merge vers cible partagée/protégée (`main`) | Choix du mode d'exécution |
| `auto_pr_merge=false` (verrouillé, `contracts.py:95`) | Messages d'avancement bloquants |

**Distinction de merge (cœur du design).** Deux natures de merge, à ne jamais confondre :
- **Merge local par EPIC** → vers la **branche de run** (locale), conditionné au **double gate +
  non-régression verts**. C'est le *mécanisme d'enchaînement*, réversible. → **Autonome**.
- **Merge final vers `main`/cible partagée** → push/PR, irréversible et visible. → **Humain
  (revue finale)**. C'est ce que protège « jamais de merge sans revue ».

## 3. Artefacts produits (livrable)

```
docs/superpowers/
  unattended-run-playbook.md   # la procédure : lifecycle + politiques + prompt orchestrateur
  templates/
    PLAN.md                    # tracker maître des EPICs (statut + déps + KPIs + budget)
    DECISIONS.md               # pré-vol groupé + défauts appliqués + questions ouvertes
```

`RUN_LOG.md` (journal append-only horodaté) est instancié par run depuis un gabarit **inclus dans
le playbook** — pas un 4ᵉ template à maintenir.

## 4. Cycle de vie d'un run — 2 gates humains

**Phase −1 — Configuration de départ (reflet de `select_onramp`, automatique).** Les 3
configurations de travail sont déjà routées par `conductor/onramp/select_onramp` : (1) from-scratch
→ `greenfield`/`ScaffoldOnramp` ; (2) continuation méthodo → `brownfield` repo conforme/`NoOnramp`
(pas de scaffold, baseline → non-régression, EPICs nouvelles seulement, tags repris à `epic-<n+1>`) ;
(3) externe → `brownfield`/`AdapterOnramp`|`BuilderOnramp` + HITL-0 + `intent`. Toutes produisent le
même `Substrate` → les phases 0-2 ci-dessous sont **identiques pour les 3**.

```
┌─ Phase 0 — PLAN & PRÉ-VOL ──────────────── ⛔ GATE 1 (humain, unique)
│   • macro-brainstorm → liste des EPICs → PLAN.md (tous "todo", déps, ordre)
│   • scan de TOUTES les EPICs → extraction des décisions anticipables
│   • UN questionnaire groupé (chaque choix = recommandation par défaut + « tout accepter »)
│   • CHOIX de la politique de merge GATE 2 (§6) — posé ici, avant la 1ʳᵉ EPIC
│   • estimation budget/temps + (gros périmètre) proposition slice MVP d'abord
│   • → DECISIONS.md figé ; consentement unique « GO unattended »
│
├─ Phase 1 — BOUCLE AUTONOME ─────────────── (aucun arrêt humain hors §5/§6)
│   pour chaque EPIC (ordre des déps ; EPICs indépendantes en parallèle) :
│     brainstorm → spec (auto-validée, consulte DECISIONS.md) → plan
│       → exécution subagent-driven → double gate + non-régression
│       → merge LOCAL si vert (+ tag, §6) → maj PLAN.md + RUN_LOG.md
│       → récap+KPIs (non bloquant) → démarre l'EPIC suivante automatiquement
│
└─ Phase 2 — REVUE FINALE ────────────────── ⛔ GATE 2 (humain, unique)
    • récap consolidé PAR EPIC (adossé aux tags) : titre, KPIs, décisions par défaut, diff résumé
    • EPICs `blocked` + questions ouvertes + coût/temps vs budget
    • validation explicite pour merger la branche de run sur `main`. RIEN mergé avant.
```

## 5. Politiques d'exécution autonome (Phase 1)

**Défaut-sinon-stop (décisions émergentes).** Une question imprévue surgit :
- **Anticipable** → déjà tranchée au pré-vol (zéro interruption).
- **Émergente non bloquante** → appliquer le **défaut le plus raisonnable**, le consigner dans
  `DECISIONS.md` (hypothèse + justification), **continuer**.
- **Irréversible / destructive / sécurité-conformité / hors-mandat / contournement d'un
  garde-fou** → **NE PAS deviner.** Marquer l'EPIC `blocked`, poursuivre les indépendantes,
  surfacer à la revue finale.

**Échec & résilience.**
- Double gate rouge → jusqu'à **3 retries** (aligné `GATE_MAX_RETRIES`, `supervisor.py:28`) →
  sinon EPIC `blocked` + poursuite des indépendantes.
- **Reprise idempotente** : `PLAN.md` (statuts) = checkpoint ; un run interrompu redémarre à la
  1ʳᵉ EPIC non `done`, sans refaire le `done` ni retaguer.
- **Budget** : plafond temps/coût + `max_parallel` dans `PLAN.md` ; arrêt propre au seuil avec
  récap reprenable.
- **Avancement asynchrone** : jamais de message bloquant ; `PLAN.md` + `RUN_LOG.md` à jour ;
  **une notification** aux seuls jalons (GATE 1/2, `blocked`, fin de run).

## 6. GATE 2 — politique de merge (choix posé au pré-vol)

Avant la 1ʳᵉ EPIC, l'orchestrateur pose UNE question (recommandation en tête) et explique
l'impact **chiffré**. Le choix est enregistré dans `DECISIONS.md`.

> « Veux-tu revoir chaque EPIC avant son intégration, ou laisser le run intégrer en autonomie et
> tout revoir à la fin ? »
>
> - **A. Auto-intégration (recommandé)** — chaque EPIC verte est mergée automatiquement sur la
>   branche de run, sans arrêt ; tu es seulement *informé* (notification) et la suivante démarre.
>   Impact : ~0 arrêt intermédiaire → débit maximal. « Lance et reviens ».
> - **B. Revue avant chaque merge** — arrêt avant chaque intégration pour ton feu vert.
>   Impact : **N arrêts pour N EPICs** → contrôle maximal, run nettement plus long.
> - **C. Revue des EPICs risquées seulement** — auto-intégration par défaut, arrêt uniquement
>   pour les EPICs marquées « sensibles » au pré-vol (migrations, sécurité, irréversible).

**Invariants — quel que soit le choix (jamais contournés) :**
- Les merges automatiques sont **LOCAUX** : toujours sur **la même branche de run**, JAMAIS vers
  `main` ni via PR auto. `auto_pr_merge` reste **false**.
- On ne merge+tague une EPIC que si **double gate + non-régression VERTS**. Une EPIC `blocked`
  n'est ni mergée ni taguée ; elle est surfacée à la revue finale.
- Après chaque intégration réussie : **tag incrémental** `run/<slug>/epic-<n>` (immutable ; à la
  reprise, ne pas retaguer une EPIC `done`) + entrée dans `RUN_LOG.md`.
- **Si une revue (B/C) rejette** une EPIC : la rouvrir avec le feedback (retry borné à 3), sinon
  `blocked` ; le run poursuit les EPICs indépendantes.
- EPICs parallèles : worktrees **réintégrés séquentiellement** sur la branche de run,
  non-régression évaluée à chaque intégration.

**Revue finale (seul merge vers `main`) :** récap par EPIC adossé aux tags + EPICs `blocked` +
questions ouvertes, puis validation explicite pour merger la branche de run sur `main`.

## 7. Schéma des templates

**`PLAN.md`**
```markdown
# Run <slug> — Plan maître
> budget: <temps/coût> · max_parallel: <n> · politique merge: <A|B|C> · branche: run/<slug>

| # | EPIC | dépend de | statut | gate | tests | durée | tag |
|---|------|-----------|--------|------|-------|-------|-----|
| 1 | …    | —         | done   | ✅   | 42    | 12m   | run/<slug>/epic-1 |
| 2 | …    | 1         | in-progress | … |    |       |     |
| 3 | …    | —         | blocked: <raison> | ❌ | | |     |
```
Statuts : `todo` · `in-progress` · `done` · `blocked: <raison>`.

**`DECISIONS.md`**
```markdown
# Décisions — Run <slug>
## Pré-vol (figé au GATE 1)
| Choix | Options | Défaut recommandé | Réponse retenue |
|-------|---------|-------------------|-----------------|
| Politique de merge | A/B/C | A (auto-intégration) | … |
| … | | | |

## Défauts appliqués en run (horodatés)
- [HH:MM] EPIC <n> — <décision> : défaut <x> appliqué — justification.

## Questions ouvertes / bloquantes
- EPIC <n> — <question irréversible> → `blocked`, en attente de la revue finale.
```

**`RUN_LOG.md`** (gabarit inclus dans le playbook) : append-only, une ligne par évènement
`[horodatage] EPIC <n> · <phase|gate|décision|tag|notification> · <détail>`.

## 8. Hors périmètre (différé)

- Tout code conductor (helper de génération du `PLAN.md`, etc.) — choix « process only ».
- Modification des 2 HITL produit A→E (inchangés ; orthogonaux à ce mode).
- Automatisation de la notification (mécanisme concret) — la procédure dit « notifier », le canal
  reste à l'orchestrateur.

## 9. Décisions prises

- **Locus** : artefacts de process (pas de code conductor).
- **Arrêts humains** : 2 points globaux par run (GATE 1 pré-vol, GATE 2 revue finale).
- **GATE 2 réglable** : politique de merge A/B/C choisie au pré-vol, défaut A.
- **Merge** : local autonome (branche de run, tags) ; `main` sous revue finale uniquement.
- **3 artefacts** (playbook + PLAN.md + DECISIONS.md) ; `RUN_LOG.md` via gabarit inclus.

## 10. Self-review

- **Placeholders** : aucun (`<slug>`/`<n>` sont des variables de gabarit, intentionnelles).
- **Cohérence** : la politique de merge §6 respecte la frontière §2 (auto = local, `main` =
  humain) ; `auto_pr_merge=false` jamais contredit.
- **Couverture** : les 4 idées initiales (plan à statut, affichage par EPIC, enchaînement auto,
  pré-vol de décisions) + complétions (défaut-sinon-stop, async, reprise, budget, parallélisme,
  GATE 2 réglable, tags) sont toutes adressées.
- **Ambiguïté** : « merge automatique » explicitement borné à « local sur branche de run ».
