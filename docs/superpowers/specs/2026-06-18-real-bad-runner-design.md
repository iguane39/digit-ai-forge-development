# Design — `/bad` réel via `claude -p` + observation `gh`

> Date : 2026-06-18 · Statut : **validé en brainstorming**.
> Portée : brancher le 2ᵉ effet réel — l'exécution autonome de sprint par le skill `/bad` —
> derrière le pont `CliRunner`, avec une posture de sécurité explicite.

## 1. Objectif & décisions de cadrage

- **Posture = B (autonome in-place, garde-fous natifs)** : on s'appuie sur l'isolation native de
  BAD (1 worktree git/story), `AUTO_PR_MERGE=false` forcé, branch protection `main`, opt-in env ;
  `--dangerously-skip-permissions` accepté car BAD isole par worktree.
- **Observation = A (via `gh`)** : après le run, `gh pr list --json` est la source de vérité ;
  on dérive `StoryOutcome` des PR ouvertes.
- L'audit Digit-AI déconseille le mode totalement autonome sur un repo client → l'opt-in est
  **bruyant** et le compromis réseau est documenté.

## 2. Composants (étend `conductor/harness/`)

- **`GhRunner` (Protocol) + `SubprocessGh`** (`harness/gh.py`) — `list_prs(cwd) -> list[dict]`
  via `gh pr list --state open --json number,title,headRefName,statusCheckRollup,url`. Injectable.
- **`SubprocessClaudeCli` étendu** — param `skip_permissions: bool = False` ; si vrai, ajoute
  `--dangerously-skip-permissions`. Off par défaut.
- **`ClaudeCliBadRunner`** (`harness/bad_runner.py`, implémente `BadRunner`) :
  - `run_sprint(layout)` : déclenche `/bad` via `CliRunner.run(trigger, layout.project_root)`
    (trigger en langage naturel, plus robuste que la commande slash) ; puis observe via
    `GhRunner.list_prs` → mappe chaque PR en `StoryOutcome` (`story_id` ← `headRefName`,
    `code_ok` ← `statusCheckRollup` sans échec, `pr_url` ← `url`).
  - `remediate(story_id, layout)` : re-déclenche `/bad` ciblé puis ré-observe la PR de la story.
  - Le runner construit par défaut un `SubprocessClaudeCli(skip_permissions=True)` + `SubprocessGh()`.
- **`resolve_bad_runner()`** (`harness/resolve.py`) — `ClaudeCliBadRunner` **seulement si**
  `CONDUCTOR_ENABLE_REAL_BAD=1` + `claude` + `gh` présents ; sinon `DefaultBadRunner` (stub).
  `supervisor` prend son `bad` par défaut du résolveur (import lazy).

## 3. Flux de données

```
superviser(layout, bad=resolve_bad_runner())
  → bad.run_sprint(layout)
    → CliRunner.run(trigger, project_root)   # /bad autonome (skip_permissions), 1 worktree/story, ouvre PR
    → gh pr list --json                       # observation
    → [StoryOutcome(story_id, code_ok, pr_url) …]
  → double gate + non-régression + 3 retries + HITL 2   (inchangés)
```

## 4. Sûreté

- **Opt-in bruyant** : `CONDUCTOR_ENABLE_REAL_BAD=1` ; défaut → `DefaultBadRunner` (lève si exécuté).
- `--dangerously-skip-permissions` **confiné** au BAD runner réel ; BAD isole par worktree/story.
- **`AUTO_PR_MERGE=false` garanti par le type** (`BadConfig.auto_pr_merge: Literal[False]`) +
  la config `bad:` écrite par D → aucun merge automatique. (Garanti au type : pas de check runtime
  mort.)
- **Jamais de merge** : HITL 2 (superviseur) inchangé ; recommandation `main` sous branch protection.
- Compromis réseau de l'autonomie documenté (playbook + spec).

## 5. Tests

- **Unitaires (CI, déterministes)** : faux `CliRunner` (enregistre les prompts) + faux `GhRunner`
  (PR canned) → `run_sprint` mappe correctement ; `remediate` ré-observe ; logique `code_ok`
  (échec CI → False) ; `resolve_bad_runner` (env on/off, claude/gh présents/absents) ;
  `skip_permissions` ajoute bien le flag.
- **Pas de test automatisé du *vrai* `/bad`** : contrairement à l'analyzer (lecture seule), `/bad`
  **mute le repo et ouvre des PR** → effets de bord inacceptables même *gated*. À la place :
  **procédure de run pilote documentée** (playbook) ; l'inconnue « `claude -p` déclenche-t-il
  `/bad` ? » est levée manuellement sur le pilote.

## 6. Séquencement

1. `GhRunner` + `SubprocessGh`.
2. `SubprocessClaudeCli` étendu (`skip_permissions`).
3. `ClaudeCliBadRunner` (run_sprint + remediate + mapping).
4. `resolve_bad_runner()` + branchement lazy du superviseur.
5. Note sûreté & run pilote (playbook EN + spec).

## 7. Hors périmètre (différé, tracé)

- BMAD réel (planification agentique).
- Bascule du défaut prod vers le BAD réel (au-delà de l'opt-in).
- Test automatisé d'un vrai sprint `/bad`.
- Note playbook multilingue (5 langues), ellipsis stderr (suivis pré-existants).

## 8. Décisions (toutes prises)

Posture B · Observation A · opt-in `CONDUCTOR_ENABLE_REAL_BAD` · tests fakes (pas de vrai run
automatisé). Aucune question ouverte bloquante.
