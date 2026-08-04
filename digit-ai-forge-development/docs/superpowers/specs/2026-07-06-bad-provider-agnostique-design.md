# Rendre le sprint `/bad` provider-agnostique (GitHub + Azure DevOps) — Design

> **Contrainte non négociable :** BAD (`vendor/bad/`, @v1.2.0, MIT) n'est **jamais** forké ni modifié.
> On l'adapte par l'**environnement** (un shim `gh` en tête de PATH), pas par le code.

**Date :** 2026-07-06 · **Branche :** `feat/bad-provider-agnostic` · **Snapshot BAD :** `db95d2c`

---

## 1. Problème

Le conductor observe déjà les PR de façon agnostique via `GitProvider` (P-04 : GitHub réel + Azure
DevOps réel #35 + GitLab stub). **Mais** le sprint lui-même est exécuté par le skill `/bad`, lancé
en sous-processus autonome via le CLI `claude` (`ClaudeCliBadRunner._cli.run`). À l'intérieur, BAD
pilote son pipeline 7 étapes avec la CLI **`gh`** (GitHub only). Sur un dépôt Azure DevOps, ces
appels `gh` échouent → le sprint ne peut pas tourner.

## 2. Inventaire (preuve de complétude, BAD @v1.2.0 `db95d2c`)

Balayage de `vendor/bad/` : **34** invocations `gh`, **6** `api.github.com`, **9** `github.com`.
Surface réelle (9 sous-commandes), classée :

| Catégorie | Surface `gh` | Preuves `fichier:ligne` (vendor/bad/) |
|---|---|---|
| observe | `gh pr list` · `gh pr view` · `gh pr diff` | coordinator/pattern-gh-curl-fallback.md:18,21,32,35 · pattern-monitor.md:58 · subagents/phase0-graph.md:15,17 · phase3-merge.md:15,63 · phase4-assessment.md:14 · SKILL.md:373 |
| read-CI | `gh pr checks` · `gh run view` *(Actions)* | pattern-gh-curl-fallback.md:48,51,65,81 · phase3-merge.md:40,44,47 · SKILL.md:346,353,354 · pattern-monitor.md:66 |
| merge | `gh pr merge` | SKILL.md:555 · pattern-gh-curl-fallback.md:102 · phase3-merge.md:5,54,58 |
| issue | `gh issue list` · `gh issue create` | pattern-gh-curl-fallback.md:67,70 · phase0-graph.md:25,27 · phase0-prompt.md:47 |
| auth | `gh auth token` · `gh auth status` | pattern-gh-curl-fallback.md:8 · phase0-prompt.md:36 |
| create-PR | *(aucun `gh pr create`)* → `git push` | phase0-prompt.md:62 · phase3-merge.md:34 |
| remote/fallback | parse `github.com` + curl `api.github.com` si `gh` indispo | 9 + 6 occurrences (pattern-gh-curl-fallback.md) |

**Deux constats confirmés par preuve :**
1. Pas de `gh pr create` en v1.2.0 → les PR naissent d'un `git push` (agnostique, rien à traduire).
2. Le fallback `api.github.com` ne se déclenche **que si `gh` est absent** → un shim `gh` toujours
   présent le **court-circuite** (le shim ne se déclenche jamais pour un dépôt AzDO).

## 3. Approche retenue (Direction 1 + 3)

Un **shim exécutable `gh`** placé en tête de PATH par le superviseur **ssi
`detect_provider == azure-devops`**. Le shim traduit exactement les 9 sous-commandes inventoriées
vers `az repos`/`az pipelines`, en **émettant le schéma JSON attendu par BAD** (réutilise
`SubprocessAz` / `AzureDevOpsProvider` de #35). GitHub : PATH normal, `gh` réel, **strictement
inchangé** (non-régression).

### Alternatives écartées
- **Forker BAD** → viole la contrainte n°1 (MIT, épinglé).
- **Patcher `vendor/bad`** → dérive de l'upstream, casse la mise à jour au tag.
- **Variable `BAD_GIT_PROVIDER`** → n'existe pas dans BAD v1.2.0 (aucune preuve).

## 4. Composants (unités isolées)

| Fichier | Responsabilité | Dépend de |
|---|---|---|
| `conductor/harness/gh_shim/translate.py` | **Cœur pur** : `translate(argv) -> ShimResult(stdout, stderr, returncode)`. Dispatch par sous-commande → `az` via un `AzBackend` injectable. Aucun I/O direct. | `SubprocessAz` (backend) |
| `conductor/harness/gh_shim/__main__.py` | Entrée CLI : lit `sys.argv`, appelle `translate`, écrit stdout/stderr, `sys.exit(code)`. | `translate` |
| `conductor/harness/gh_shim/install.py` | Écrit les lanceurs `gh` (POSIX, `+x`) et `gh.cmd` (Windows) dans un bin dir dédié ; renvoie le dossier à préfixer au PATH. | — |
| `conductor/process.py` | `ProcessRunner.run(..., env=None)` : overlay d'environnement optionnel (non-régression : `None` = comportement actuel). | — |
| `conductor/harness/claude_cli.py` | `SubprocessClaudeCli(env_overlay=None)` : propage l'overlay au runner. | `ProcessRunner` |
| `conductor/harness/bad_runner.py` | Calcule l'overlay (`{PATH: bin_dir + os.pathsep + PATH}`) **ssi** `detect_provider == azure-devops` ; le passe au CLI. | `install`, `detect_provider` |

## 5. Mapping `gh → az` (par sous-commande réelle)

| `gh` (réel) | `az` | Schéma JSON émis | Écart |
|---|---|---|---|
| `gh pr list [--json f,g]` | `az repos pr list --status active` | `[{number, headRefName, url, statusCheckRollup}]` | — |
| `gh pr view <n> [--json]` | `az repos pr show --id <n>` | idem, 1 objet | — |
| `gh pr checks <n>` | policies → rollup (via #35) | lignes `name\tstatus` + exit≠0 si non-vert | statusCheck ≠ policy (mappé) |
| `gh pr diff <n>` | `git diff origin/{base}...origin/{head}` | diff texte | pas d'`az` 1-commande → `git diff` |
| `gh pr merge <n>` | `az repos pr update --id <n> --status completed` | — | HITL 2 maître (auto_pr_merge=false) |
| `gh run view [id]` | `az pipelines runs show` **ou** CI locale | statut de run | Actions ≠ Pipelines (best-effort) |
| `gh issue list` | `az boards work-item query` | `[{number, title}]` | mapping partiel, tracé |
| `gh issue create` | `az boards work-item create` | `{number, url}` | idem |
| `gh auth token` / `status` | `az account get-access-token` / `show` | token / statut | — |

**Anti faux-positif :** toute sous-commande non mappée sûrement → exit≠0 + message tracé sur
stderr (jamais un faux succès silencieux). `gh pr merge` reste sous HITL 2 (le conductor
n'auto-merge jamais : `auto_pr_merge=false` garanti par le type).

## 6. Sélection & non-régression GitHub

- Sélection : `detect_provider(project_root)` (déjà existant). `github`/inconnu → **aucun overlay**,
  PATH normal, `gh` réel. `azure-devops` → overlay PATH avec le bin du shim en tête.
- `ProcessRunner.run(env=None)` : `None` ⇒ hérite de l'environnement courant (comportement 100 %
  inchangé). Overlay ⇒ `subprocess.run(env=...)`.
- Tests de non-régression : sur un remote `github.com`, `bad_runner` ne calcule aucun overlay et le
  CLI est appelé sans `env`.

## 7. Tests (double gate)

- `test_gh_shim_translate.py` : une classe de tests **par sous-commande** (backend `az` factice),
  vérifiant le schéma JSON iso-`gh` et les codes de sortie (vert/rouge/inconnu).
- `test_gh_shim_install.py` : les lanceurs sont écrits, exécutables (POSIX), et le bin dir est
  renvoyé.
- `test_process_env.py` : `run(env=...)` applique l'overlay ; `env=None` inchangé.
- `test_bad_runner_shim.py` : overlay calculé ssi `azure-devops` ; **aucun** overlay sur GitHub.
- Gate : `ruff` + `mypy --strict` + `pytest` verts ; `vendor/` exclu du lint (code tiers épinglé).

## 8. Hors périmètre (différé, tracé)

- GitLab réel (reste `UnsupportedProvider`).
- `gh run view` → Pipelines complet : best-effort v1 (statut simple ou repli CI locale) ;
  l'observation fine des runs Actions↔Pipelines fera l'objet d'un chantier dédié si le pilote
  AzDO le réclame.
- Mapping `issue` ↔ `az boards` exhaustif (types de work-item, champs) : couverture minimale v1.
