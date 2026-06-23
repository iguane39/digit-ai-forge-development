# Design — BMAD réel via `claude -p` (3ᵉ et dernier effet réel)

> Date : 2026-06-18 · Statut : **validé en brainstorming**.
> Portée : déclencher la planification agentique BMAD via le pont `CliRunner`, gated par HITL 1.
> Complète le pont : analyzer ✅ + `/bad` ✅ + **BMAD** → chaîne A→E intégralement runnable (opt-in).

## 1. Décisions de cadrage
- **Posture = A (déclenchement autonome)** : un `ClaudeCliBmadPlanner` déclenche la planif via
  `claude -p`, observe `epics.md`, opt-in env ; **HITL 1 valide** le PRD/archi avant tout dev.
- Risque faible : **documents uniquement** (pas de mutation de code, pas de merge), gated HITL 1.
- Fallback intégré : sans opt-in → `DefaultBmadPlanner` (install + collecte + HitlPending).

## 2. Composants (`conductor/harness/`)
- **`ClaudeCliBmadPlanner`** (`harness/bmad_planner.py`, implémente `BmadPlanner`) :
  `plan(substrate)` déclenche la planif via `CliRunner.run(trigger, substrate.repo_path)`
  (CLI par défaut `SubprocessClaudeCli(skip_permissions=True)` — écritures fichier + `npx`
  headless), puis lit `_bmad-output/planning-artifacts/epics.md` (absent → `HitlPending`).
  Renvoie `BmadPlan(prd_path, architecture_path, epics_md, stories=[])` (`stories` vide : BAD
  reconstruit le graphe — spike S-1), `hitl1_approved=False`.
- **`resolve_bmad_planner()`** (`harness/resolve.py`) — `ClaudeCliBmadPlanner` si
  `CONDUCTOR_ENABLE_REAL_BMAD=1` + `claude` présent ; sinon `DefaultBmadPlanner`.

## 3. Branchement (lazy, anti-cycle)
- `bmad_bridge.lancer_planification` : défaut `planner = resolve_bmad_planner()` (greenfield).
- `ComplementPlanner` : défaut `inner = resolve_bmad_planner()` (complément brownfield).
- Imports lazy uniquement : `harness.bmad_planner` n'importe pas `bmad_bridge` ; `resolve` importe
  `bmad_bridge`/`bmad_planner` dans le corps de fonction ; `bmad_bridge`/`complement` importent
  `resolve` dans le corps. → pas de cycle.

## 4. Flux
`lancer_planification(substrate, planner=resolve_bmad_planner())` → `claude -p` (BMAD écrit
`_bmad-output/`) → lit `epics.md` → `BmadPlan` → **HITL 1** → D → E.

## 5. Sûreté
Opt-in bruyant ; docs only (pas de code muté, pas de merge) ; **HITL 1 = garde-fou** ;
`skip_permissions` confiné au planner réel ; défaut → `DefaultBmadPlanner` (aucune planif
autonome involontaire).

## 6. Tests
- **Unitaires (fakes)** : faux `CliRunner` → `plan` déclenche (prompt contient « BMAD ») puis lit
  un `epics.md` pré-créé → `BmadPlan` ; `epics.md` absent → `HitlPending` ; `resolve_bmad_planner`
  (env on/off) ; wiring (`lancer_planification` planner=None utilise le résolveur).
- **Pas de run réel automatisé** (comme `/bad` : `npx install` + écritures + réseau) → procédure
  pilote documentée (playbook). CI 100 % déterministe.

## 7. Séquencement
1. `ClaudeCliBmadPlanner`.
2. `resolve_bmad_planner()`.
3. Branchement lazy (`lancer_planification` + `ComplementPlanner`).
4. Note pilote (playbook EN).

## 8. Hors périmètre (différé)
Run réel automatisé ; flip défaut prod ; parsing des stories (BAD reconstruit le graphe) ;
suivis pré-existants (stderr ellipsis, playbook multilingue, epics.md composite).

## 9. Décisions (toutes prises)
Posture A · opt-in `CONDUCTOR_ENABLE_REAL_BMAD` · observation fichier · tests fakes (pas de vrai
run automatisé). Aucune question ouverte bloquante.

## 10. Mise à jour B-11 (2026-06-23) — produire les artefacts, ne PAS installer le framework
Le pilote a montré que l'installeur BMAD est un **TUI interactif non automatisable en headless**
(les flags `--yes`/`--tools` ne le court-circuitent pas ; B-10 était une hypothèse insuffisante).
Correctif : le conductor **n'installe plus** BMAD. Le `ClaudeCliBmadPlanner` instruit l'agent de
**produire directement** PRD/architecture/epics au format BMAD ; le `DefaultBmadPlanner` ne tente
aucun install et **pause HITL 1** si les artefacts sont absents (à rédiger par l'agent réel ou à la
main). Ce qui compte en aval, ce sont les **artefacts** (consommés par `parse_epics`/BAD), pas le
framework installé. Constantes `BMAD_INSTALL`/`BMAD_VERSION` supprimées. Installer le vrai framework
reste possible **hors-bande** (terminal TTY) si désiré.
