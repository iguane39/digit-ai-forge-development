# Design — `SubagentAnalyzer` réel via `claude -p` (pont Python → harness)

> Date : 2026-06-18 · Statut : **validé en brainstorming**.
> Portée : rendre l'ingestion brownfield *réelle* en branchant le premier adapter
> Python → Claude Code (`claude -p`), sans toucher à `/bad`/BMAD ni casser le déterminisme CI.

## 1. Objectif & contexte

La forge est entièrement testée par *fakes* ; trois points d'intégration restent des stubs
(`SubagentAnalyzer`, `DefaultBmadPlanner` réel, `DefaultBadRunner`). Ce design livre **le premier
effet réel** — l'ingestion par sous-agent — selon le mécanisme **hybride (C)** décidé :
orchestration Python pure + **adapters `claude -p`** pour les effets ; `/bad` reste piloté-par-agent.

**Décisions de cadrage :**
- **Mécanisme = C** : `conductor` reste un paquet Python ; les effets réels passent par un adapter
  qui shelle `claude -p`.
- **Périmètre = A** : seul `SubagentAnalyzer` devient réel. `/bad` et BMAD différés.
- **Test = A** : unitaires par *fake* (CI déterministe) + 1 test d'intégration *gated* (réel).

## 2. Architecture & composants

Nouveau paquet **`conductor/harness/`** (pont Python → Claude Code, réutilisable ensuite) :

- **`CliRunner` (Protocol)** + **`SubprocessClaudeCli`** — `run(prompt: str, cwd: Path) -> str`.
  Lance `claude -p <prompt> --output-format json` dans `cwd`, parse l'enveloppe JSON, renvoie le
  champ `result` (texte final de l'agent). Injectable (fake en test).
- **`ClaudeSubagentAnalyzer`** (implémente le protocole `Analyzer` existant) — **hybride** :
  1. `HeuristicAnalyzer` pour les *faits durs* (`top_level`, `has_pyproject`, `has_frontend`, …) ;
  2. un prompt d'*interprétation* envoyé via `CliRunner` → JSON (`summary`, `conventions`, `debt`) ;
  3. **fusion** : `arch_map = {**faits, **interprétation}`.
- **`resolve_analyzer() -> Analyzer`** — sélecteur : `ClaudeSubagentAnalyzer` **seulement si**
  `CONDUCTOR_USE_CLAUDE_ANALYZER=1` (et CLI `claude` détectable), sinon `HeuristicAnalyzer`.

Les onramps (`AdapterOnramp`, `BuilderOnramp`) prennent leur `analyzer` par défaut de
`resolve_analyzer()` → comportement réel opt-in par variable d'env ; **défaut = heuristique**
(aucun appel `claude` involontaire en CI).

## 3. Flux de données

```
onramp(analyzer=resolve_analyzer())
  → analyze(repo)
    → faits = HeuristicAnalyzer().analyze(repo)
    → result = CliRunner.run(prompt(repo, faits), cwd=repo)   # claude -p --output-format json
    → interpretation = json.loads(result)   # {summary, conventions, debt}
    → arch_map = {**faits, **interpretation}
```

## 4. Gestion d'erreur & sûreté

- `SubprocessClaudeCli` : exit ≠ 0, timeout, ou enveloppe JSON illisible → `RuntimeError` explicite.
- `ClaudeSubagentAnalyzer` **dégradation gracieuse** : si `result` est absent/non-parsable, on
  retombe sur les **faits heuristiques seuls** + `arch_map["interpretation"] = "indisponible"`
  (un échec d'interprétation ne casse jamais le run).
- **Zéro token en CI** : le réel n'est appelé que si `CONDUCTOR_USE_CLAUDE_ANALYZER=1` ; les
  unitaires utilisent un faux `CliRunner`.
- **Lecture seule** : analyse uniquement, aucune permission élargie (`--dangerously-skip-permissions`
  reste pour le futur `/bad`).

## 5. Tests

- **Unitaires (CI, déterministes)** :
  - `SubprocessClaudeCli` avec un faux exécuteur de sous-processus (enveloppe `{"result": "..."}`),
    + cas exit≠0 / JSON cassé → `RuntimeError`.
  - `ClaudeSubagentAnalyzer` avec faux `CliRunner` : fusion faits+interprétation ; **fallback**
    gracieux sur `result` non-JSON.
  - `resolve_analyzer` : env on → `ClaudeSubagentAnalyzer` ; absent → `HeuristicAnalyzer`.
- **Intégration *gated*** : un test qui shelle réellement `claude -p` sur un mini-repo fixture,
  **sauté** sauf `RUN_CLAUDE_INTEGRATION=1` et `claude` présent. Mode d'emploi exécutable du run pilote.

## 6. Séquencement

1. `CliRunner` + `SubprocessClaudeCli` (+ unitaires fake).
2. `ClaudeSubagentAnalyzer` hybride + fallback (+ unitaires fake).
3. `resolve_analyzer()` (env opt-in) + branchement par défaut des onramps sur le résolveur.
4. Test d'intégration *gated* + note « run pilote » dans le playbook.

## 7. Hors périmètre (différé, tracé)

- `/bad` réel (`ClaudeCliBadRunner` + permissions/sécurité, `--dangerously-skip-permissions`).
- BMAD réel (planification agentique).
- Bascule du défaut de production vers l'analyzer réel (au-delà de l'opt-in par env).
- `epics.md` composite (`intent=both`) — suivi pré-existant.

## 8. Décisions (toutes prises)

- Mécanisme C (Python pur + adapters `claude -p`) · Périmètre A (analyzer seul) · Test A
  (fakes CI + intégration gated). Aucune question ouverte bloquante.
