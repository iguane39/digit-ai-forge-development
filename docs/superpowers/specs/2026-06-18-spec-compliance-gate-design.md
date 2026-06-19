# Design — Gate de conformité au spec (greffe superviseur)

> Date : 2026-06-18 · Statut : **brainstorming validé** (en attente de revue de la spec).
> Origine : mesure spec-compliance sur les EPICs passées (13 écarts gate-invisibles / 83 exigences,
> dont 4 matériels) → un gate de conformité au spec est justifié, calibré **remédiable**.
> Portée : greffer un **juge** entre le double gate et HITL 2 dans le superviseur. **Ne réimplémente
> PAS BAD** (décision 01) : le juge est un lecteur (PR + critères d'acceptation), pas un développeur.

## 1. Objectif

Combler le seul trou objectif de la stack BMAD/BAD/design.md : la **conformité au spec**. Un double
gate vert (ruff/mypy/pytest + design) prouve « ça compile/teste », pas « on a construit la bonne
chose ». Le juge confronte chaque PR aux `acceptance` de sa story pour détecter **sous-build**
(critère non tenu) et **sur-build** (comportement non demandé) — écarts qu'aucun gate n'attrape.

## 2. Décisions de cadrage (validées en brainstorming)

- **A · Posture = remédiable.** Le verdict spec rejoint le prédicat de passage du superviseur →
  remédiation **bornée** (les 3 retries existants, `GATE_MAX_RETRIES`), puis `blocked`. Pas de
  blocage dur (la majorité des écarts mesurés sont faibles).
- **B · Portée = sous-build bloquant (via retry) + sur-build consultatif.** Un critère d'acceptation
  non tenu fait **échouer** le gate. Un comportement au-delà du spec est **signalé** (`findings`)
  mais **ne bloque pas**.
- **C · Activation = opt-in `CONDUCTOR_ENABLE_SPEC_REVIEW`.** Défaut OFF = pass-through déterministe
  (CI 100 % déterministe, comportement actuel inchangé). Réel = `claude -p`, pilote documenté.

## 3. Composants (`conductor/`)

- **`SpecVerdict`** (`contracts.py`, miroir de `GateVerdict`) :
  `passed: bool`, `findings: list[dict[str, str]]`, `log_ref: str = ""`.
  Convention des findings : `{"kind": "under-build"|"over-build", "criterion": "...", "detail": "..."}`.
  Seuls les findings `under-build` font `passed=False` ; les `over-build` sont consultatifs.
- **`SpecComplianceReviewer`** (Protocol, `supervisor.py`) :
  `review(story: Story, outcome: StoryOutcome) -> SpecVerdict`.
- **`DefaultSpecReviewer`** (`supervisor.py`) : déterministe, **pass-through**
  (`SpecVerdict(passed=True, findings=[])`). Aucun appel réseau. Préserve le comportement par défaut.
- **`ClaudeCliSpecReviewer`** (`harness/spec_reviewer.py`, opt-in) : déclenche la revue via
  `CliRunner.run(trigger, project_root)` (CLI par défaut `SubprocessClaudeCli`), rubrique = les
  `acceptance` de la story confrontées au **diff de la PR** (`outcome.pr_url`). Renvoie un
  `SpecVerdict` (les critères non tenus → findings `under-build` ; les ajouts → `over-build`).
  **Pas de run réel automatisé** en CI (comme `/bad`/BMAD) → procédure pilote (playbook).
- **`resolve_spec_reviewer()`** (`harness/resolve.py`) : `ClaudeCliSpecReviewer` si
  `CONDUCTOR_ENABLE_SPEC_REVIEW=1` ET `claude` présent ; sinon `DefaultSpecReviewer`.
- **`SPEC_FINDINGS.md`** (`docs/superpowers/templates/`) : registre **persistant** des findings,
  avec statut traité/non-traité, pour reprise manuelle ultérieure — voir §7.

## 4. Branchement dans le superviseur

`superviser(...)` reçoit `spec_reviewer: SpecComplianceReviewer | None = None` ; si `None`, résolu
via `resolve_spec_reviewer()` (import lazy, comme `resolve_bad_runner`). Le prédicat de passage :

```python
def _passes(o: StoryOutcome) -> bool:
    design_ok = check(o).passed
    current = {"code": o.code_ok, "design": design_ok}
    no_regression = evaluate_regression(layout.baseline or {}, current).passed
    spec_ok = reviewer.review(story_for(o), o).passed   # NOUVEAU
    return o.code_ok and design_ok and no_regression and spec_ok
```

→ un `spec_ok=False` (≥1 finding `under-build`) déclenche `runner.remediate(...)` puis re-évalue,
exactement comme un gate rouge. Au-delà des retries → story `blocked` (raison : non-conformité spec).

Note : le superviseur itère les `StoryOutcome` ; il doit pouvoir retrouver la `Story` (avec ses
`acceptance`) correspondant à un `outcome.story_id`. Le `BadSprintLayout` ne porte pas les stories
(BAD reconstruit le graphe, spike S-1) → on passe les stories au superviseur (paramètre
`stories: list[Story] | None`), à défaut le reviewer reçoit une story minimale (id seul) et le
`DefaultSpecReviewer` pass-through reste correct.

À chaque évaluation produisant des findings, le superviseur les **écrit/met à jour dans
`SPEC_FINDINGS.md`** (statut traité/non-traité, §7) — c'est la persistance pour reprise manuelle.

## 5. Sûreté / invariants préservés

- N'auto-merge rien (le juge ne touche pas au merge) ; `auto_pr_merge=false` et
  `SprintReport.merged=False` intacts ; **HITL 2 inchangé**.
- Défaut pass-through déterministe → **CI verte sans `claude`**. Opt-in bruyant.
- `skip_permissions` confiné au reviewer réel. Le juge lit la PR, ne mute rien.

## 6. Tests (fakes, CI déterministe)

- Fake reviewer `passed=False` → le superviseur remédie (3 retries) puis marque `blocked` ;
  `passed=True` → `ready-for-review` (comportement actuel).
- `SpecVerdict` : findings `over-build` seuls → `passed=True` ; ≥1 `under-build` → `passed=False`.
- `resolve_spec_reviewer` : env on / off / sans `claude`.
- Intégration superviseur : le gate spec s'ajoute aux 3 autres sans les altérer (les tests
  existants restent verts, le `DefaultSpecReviewer` ne changeant rien).
- `SPEC_FINDINGS.md` : un under-build corrigé au retry → ligne statut `traité` ; un over-build →
  ligne statut `non-traité` ; une story `blocked` → finding `non-traité`. Mode pass-through →
  aucun finding écrit.
- **Pas de run réel automatisé.**

## 7. Registre de findings centralisé (`SPEC_FINDINGS.md`)

Tous les findings sont **persistés** (pas seulement transitoires) dans un fichier dédié, instancié
par run à la racine depuis `docs/superpowers/templates/SPEC_FINDINGS.md`, avec un statut
**traité / non-traité** pour reprise manuelle ultérieure.

Schéma (une ligne par finding) :

| id | story | kind | critère | détail | sévérité | statut | note/résolution |
|----|-------|------|---------|--------|----------|--------|-----------------|
| SF-1 | 6.2 | under-build | export tokens WCAG | non couvert | moyenne | traité | corrigé au retry 2 |
| SF-2 | 6.2 | over-build | flag `--json` ajouté | non demandé | faible | non-traité | à reprendre manuellement |

Sémantique du statut (écrit par le superviseur) :
- **under-build corrigé par la remédiation** → `traité` (auto, avec note du retry où il disparaît) ;
- **over-build (consultatif)** et **story `blocked` pour non-conformité** → `non-traité` par défaut ;
- rien n'est jamais effacé : on bascule le statut, on conserve l'historique (append + maj statut).

Intégration : `RUN_LOG.md` pointe vers `SPEC_FINDINGS.md` ; la revue finale (HITL 2 / GATE 2) le
présente ; entre deux runs, l'utilisateur ouvre le fichier et traite les `non-traité` à la main (ou
les injecte dans le pré-vol du run suivant). C'est le seul registre à cycle de vie « statut »,
distinct de `DECISIONS.md` (qui fige des choix). En mode défaut (pass-through), aucun finding n'est
produit → fichier vide/absent, comportement inchangé.

## 8. Séquencement

1. `SpecVerdict` (contracts).
2. `SpecComplianceReviewer` Protocol + `DefaultSpecReviewer` + branchement `_passes` (superviseur).
3. `resolve_spec_reviewer()` (resolve).
4. `ClaudeCliSpecReviewer` (harness).
5. Template `SPEC_FINDINGS.md` + écriture/maj du statut par le superviseur.
6. Note pilote (playbook + frontière cérémonie/gouvernance : le gate spec rejoint le double gate
   côté PRÉSERVÉ).

## 9. Hors périmètre (différé)

- Flip ON par défaut en prod.
- Parsing/scoring fin des findings au-delà de under/over-build.
- Run réel automatisé en CI.
- Les **4 écarts matériels** mesurés (correctifs candidats indépendants — voir mémoire projet
  `ecarts-materiels-mesure-spec-compliance`).

## 10. Décisions prises

Posture remédiable · sous-build bloquant + sur-build consultatif · opt-in
`CONDUCTOR_ENABLE_SPEC_REVIEW` · défaut pass-through déterministe · juge = lecteur (pas dev,
décision 01 préservée) · tests via fakes · **findings persistés dans `SPEC_FINDINGS.md` (statut
traité/non-traité, reprise manuelle)**.

## 11. Self-review

- **Placeholders** : aucun (signatures, env var, schéma de findings/registre tous concrets).
- **Cohérence** : miroir fidèle du pattern des 3 pilotes (Protocol + `resolve_*` + Default + Claude
  + fakes) ; `_passes` étendu sans retirer les 3 conditions existantes ; invariants merge intacts ;
  `SPEC_FINDINGS.md` aligné sur la traçabilité existante (`RUN_LOG.md`/`DECISIONS.md`).
- **Couverture** : les 3 décisions de cadrage (A/B/C) ont chacune un composant + un test ; le point
  délicat (retrouver la `Story` depuis l'`outcome`) est traité (§4) ; la persistance des findings
  avec statut est traitée (§7) + testée (§6).
- **Ambiguïté** : « bloquant » borné à `under-build` ; `over-build` explicitement consultatif ;
  statut `non-traité` par défaut pour over-build et stories `blocked`.
