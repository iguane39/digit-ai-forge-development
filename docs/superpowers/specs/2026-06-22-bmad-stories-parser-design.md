# Design — B-3 · Parsing des stories BMAD (`epics.md` → `list[Story]`)

> Date : 2026-06-22 · Statut : **brainstorming validé**.
> Origine : backlog B-3 (keystone). Sans `acceptance` par story, le gate spec-compliance (PR #12)
> n'a pas de rubrique en greenfield BMAD. Ce parsing peuple `BmadPlan.stories`.

## 1. Objectif
`ClaudeCliBmadPlanner.plan` renvoie `stories=[]`. Extraire de `epics.md` les **métadonnées de
story** (id, epic, title, acceptance, gh_issue) → alimente la rubrique du gate spec-compliance, le
`PLAN.md`, et le lookup Story↔outcome du superviseur.

## 2. Périmètre — ce qu'on NE fait PAS
Reconstruire le graphe de dépendances : **interdit** (décision canonique 01 ; BAD le construit en
Phase 0, spike S-1). On extrait uniquement des métadonnées plates. Aucun ordonnancement.

## 3. Composants
- **`conductor/harness/epics_parser.py`** — fonction pure déterministe :
  `parse_epics(text: str) -> list[Story]`. Aucun réseau, aucune dépendance `claude` → testable en CI.
- **Câblage dans `ClaudeCliBmadPlanner.plan`** : lire le texte de `epics.md` puis
  `stories=parse_epics(text)`. Le reste du flux (HitlPending si absent) inchangé.

## 4. Heuristiques (machine à états ligne par ligne, tolérante)
- **Epic** : ligne titre `^#+ … epic <n> …` (insensible à la casse) → `epic` courant = titre (ou
  `epic-<n>`). Ferme la story en cours.
- **Story** : ligne titre contenant un id `\d+\.\d+` (ex. `6.1`) → nouvelle story (`id`, `title`).
  Le **point dans l'id** distingue une story (`6.1`) d'un epic (`6`).
- **GH Issue** : ligne `**GH Issue:** #<n>` → `gh_issue` (int) de la story courante.
- **Acceptance** : une ligne marquant une section « Acceptance / Critères d'acceptation »
  (titre `#…` ou gras `**…**`) ouvre la collecte ; les puces `- …` / `* …` suivantes sont
  ajoutées à `acceptance` jusqu'au titre suivant. Tout autre titre referme la collecte.
- Story sans section acceptance → `acceptance=[]`.

## 5. Fallback (sûreté)
Si aucune story (`\d+\.\d+`) n'est trouvée → `parse_epics` renvoie `[]`. Côté planner,
`stories=[]` = comportement actuel → le gate spec-compliance reste **pass-through** (juge sans
rubrique). Aucune régression possible.

## 6. Tests (déterministes, échantillon `epics.md`)
- Échantillon 1 epic / 2 stories avec acceptance + `GH Issue` → 2 `Story` correctes
  (id `6.1`/`6.2`, titres, acceptance non vides, gh_issue).
- Story sans section acceptance → `acceptance == []`.
- Epic id (`6`) seul n'est pas pris pour une story.
- Texte vide / prose sans `X.Y` → `[]`.
- Intégration : fake `CliRunner` qui écrit l'échantillon dans `epics.md` → `plan()` renvoie un
  `BmadPlan` avec `stories` peuplées ; `epics.md` absent → `HitlPending` (inchangé).

## 7. Décisions prises
Parser **heuristique déterministe** (pas de sous-agent : déterministe, testable, respecte la
décision 01) · **fallback `stories=[]`** · **métadonnées seules** (pas de graphe) · réutilise le
modèle `Story` existant (`contracts.py`).

## 8. Hors périmètre (différé)
- Parsing du graphe / dépendances inter-stories.
- Peuplement de `DefaultBmadPlanner` (greenfield collecté) — le parser est réutilisable, mais B-3
  cible le planner réel.
- Validation du format exact `epics.md` contre un vrai run BMAD → confirmée au **pilote B-7**.

## 9. Self-review
- **Placeholders** : aucun. **Cohérence** : `Story` inchangé ; `ClaudeCliBmadPlanner` garde son
  contrat (`BmadPlan`), seule `stories` est désormais peuplée ; fallback préserve le comportement.
- **Ambiguïté** : « story » = titre avec id `\d+\.\d+` (le point tranche vs epic). Acceptance bornée
  à sa sous-section. **Sûreté** : aucun réseau, fonction pure, fallback total.
