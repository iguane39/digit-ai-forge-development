# Backlog de portabilité de la Forge — cross-platform · stack-agnostique · remédiation in-situ

> ✅ **Traité (2026-06-24) — 13/13.** Implémenté de bout en bout :
> **E1** [#31] runner cross-platform (P-07, P-01, P-02, P-08 code) ·
> **E2+E3+E4** [#32] stack-agnostique (P-03, P-05, P-06) + GitProvider (P-04) + robustesse (P-10, P-13) ·
> **E5** [#33] profil dérivé (P-09) + actions par rôle (P-11) + scaffold sans shell (P-08 complet).
> P-12 = audit chemins → rien à corriger. `shell=True` totalement éliminé.

> Audit **lecture seule** du conductor. Snapshot audité : **`44bbb00`**
> (`digit-ai-saas-forge/digitai-saas-forge`, 39 fichiers Python, `conductor/`).
> Aucun fichier de la forge n'a été modifié par cet audit. Ce document est le livrable.

## Constat d'architecture (résumé exécutif)

La forge a **déjà amorcé** l'adaptation par stack mais ne l'a pas câblée de bout en bout :

- ✅ Il existe un protocole `CommandRunner` (code_gate.py:25) et un `TargetProfile`
  (profiles.py:14) injectables, avec **2 profils** (`FASTAPI_SAAS` : `uv run pytest` ;
  un profil node-ts : `npm test`) et une détection `detect_stack()` (detect.py:42)
  → fastapi / node-ts / unknown. Les gates sont **conditionnels** (`if profile.code_check`,
  `if profile.has_ui`).
- ❌ Mais : (1) `capture_baseline` **force `FASTAPI_SAAS`** (no_onramp.py:66) en ignorant
  `detect_stack` ; (2) `NoOnramp` **exige `pyproject.toml`** (no_onramp.py:60) → rejette tout
  repo non-Python ; (3) **deux sites court-circuitent le runner** et lancent `npx` en nom nu
  (design_gate.py:91, tokens.py:31) → `WinError 2` sous Windows ; (4) **aucune détection OS**
  (0 occurrence de `os.name`/`sys.platform`/`platform`) ; (5) **aucune abstraction du provider
  Git** — `gh` + `GITHUB_PERSONAL_ACCESS_TOKEN` codés en dur.

La correction n'est donc pas une réécriture : c'est **finir de brancher** l'abstraction
existante + **unifier les invocations** derrière un runner cross-platform unique + **abstraire
le provider Git**.

## Preuve de complétude (méthode)

| Catégorie | Commande de recherche | Occurrences | Traitées |
|---|---|---|---|
| Invocations de process externes | `rg 'subprocess\|Popen\|os\.system\|check_output\|check_call'` | 18 (dont **6 spawns réels**) | 6/6 |
| `shell=True` | `rg 'shell=True'` | 2 | 2/2 |
| Résolution binaire | `rg 'shutil\.which'` | 6 | 6/6 |
| Détection OS | `rg 'os\.name\|sys\.platform\|platform\.(system\|platform)'` | **0** | — |
| Marqueurs codés en dur | `rg 'DESIGN\.md\|pyproject\|package\.json\|_bmad-output'` | ~20 | recensés |
| Couplage GitHub | `rg 'gh \|GITHUB_\|pr list\|branch-protect'` | 3 sites | 3/3 |

**Les 6 spawns réels de process externes** (catégorie 1, exhaustif) :
1. `harness/claude_cli.py:42` — `claude` — ✅ **déjà corrigé** (`shutil.which`, ligne 37).
2. `harness/gh.py:27` — `gh pr list` — nom nu + couplage GitHub.
3. `tokens.py:34` — `npx --yes -p <pkg>` (export tokens DESIGN.md) — **nom nu → WinError 2**.
4. `gates/design_gate.py:94` — `npx --yes -p <pkg>` (lint DESIGN.md) — **nom nu → WinError 2 (bug confirmé)**.
5. `gates/code_gate.py:31` — `SubprocessRunner` → `shell=True` sur `profile.code_check`.
6. `scaffold.py:33` — runner → `shell=True` sur `copier copy …`.

---

## Backlog priorisé

Légende — **Sévérité** : 🔴 bloquant / 🟠 majeur / 🟡 mineur. **Type** : `corriger` (bug) / `compléter` (capacité).

| ID | Cat. | Élément | Preuve `fichier:ligne` | Type | Sév. | OS/Stack impacté | Correctif (patron) | Effort |
|----|------|---------|------------------------|------|------|------------------|--------------------|--------|
| **P-01** | 1 | `NpxDesignLinter` lance `["npx", …]` en nom nu | `gates/design_gate.py:91,94` | corriger | 🔴 | Windows / toutes | Passer par le **runner cross-platform** unifié (P-07) → `shutil.which("npx")` | S |
| **P-02** | 1 | Export tokens lance `["npx", …]` en nom nu | `tokens.py:31,34` | corriger | 🔴 | Windows / toutes | idem P-07 | S |
| **P-03** | 3 | `capture_baseline` force `FASTAPI_SAAS` au lieu d'utiliser `detect_stack` | `onramp/no_onramp.py:66` ; `onramp/detect.py:42` | corriger | 🔴 | non-Python | Sélectionner le `TargetProfile` **depuis `detect_stack(repo)`** (mapping stack→profil) | M |
| **P-04** | 4 | Provider Git = GitHub only (`gh`, `GITHUB_PERSONAL_ACCESS_TOKEN`) | `harness/gh.py:27-28` ; `supervisor.py:60` | compléter | 🔴 | Azure DevOps / GitLab | Interface **`GitProvider`** (list/create PR, protection) + impls GitHub/AzDO/GitLab, sélection par remote | L |
| **P-05** | 3 | `NoOnramp` exige `pyproject.toml`, rejette tout repo non-Python de la branche A | `onramp/no_onramp.py:60` ; `onramp/detect.py:26-35` | compléter | 🟠 | non-Python | Marqueur de conformité **dérivé du profil** (`pyproject` OU `package.json` OU …), pas Python en dur | M |
| **P-06** | 2 | `DEFAULT_CODE_CHECK = "uv run pytest"` par défaut hors profil | `gates/code_gate.py:22,38` | corriger | 🟠 | non-Python | Pas de défaut Python : exiger un profil ; si stack inconnue → gate `skip` tracé | S |
| **P-07** | 1 | Pas de runner d'invocation **unifié** : 4 sites appellent `subprocess` en direct, hors du protocole `CommandRunner` | `claude_cli.py:42`, `gh.py:27`, `tokens.py:34`, `design_gate.py:94` | compléter | 🟠 | Windows / toutes | **`ProcessRunner` unique** : args en **liste**, `shutil.which`, timeout, jamais `shell=True` sur entrée non fiable ; TOUS les spawns y passent | M |
| **P-08** | 1 | `shell=True` sur commande-chaîne (`copier copy …`, `code_check`) | `scaffold.py:33` ; `gates/code_gate.py:31` | corriger | 🟠 | Windows/Linux (quoting) | Passer en **liste d'arguments** via P-07 ; construire les commandes comme `list[str]`, pas comme f-string shell | M |
| **P-09** | 2 | `code_check`/`design_md_path` codés en dur dans les profils, non **dérivés** du repo | `profiles.py:31-44` | compléter | 🟠 | multi-stack | Étendre `TargetProfile` : `test_cmd`/`build_cmd`/`lint_cmd` **dérivés** de la stack (lecture `package.json` scripts, `pyproject`, Makefile…) | L |
| **P-10** | 3 | `design_gate` (NpxDesignLinter) supposé disponible dès que `has_ui` | `onramp/no_onramp.py:40-42` ; `gates/design_gate.py:77` | compléter | 🟡 | projets sans DESIGN.md | Gate design **skip tracé** si `DESIGN.md` absent (do-no-harm) au lieu d'échouer | S |
| **P-11** | 2 | Actions catalogue codées en dur `cd frontend && npm i …` | `catalog.py:74,92,104` | compléter | 🟡 | layout non-`frontend/`, non-npm | Dériver le répertoire front + gestionnaire de paquets du profil ; sinon marquer l'action non applicable | M |
| **P-12** | 5 | Marqueurs BMAD/`/bad` en chemins POSIX relatifs `_bmad-output/…` (constants `Path("…")`) | `bmad_bridge.py:20`, `sprint_config.py:20`, `harness/bmad_planner.py:19`, `contracts.py:78,106-107` | corriger | 🟡 | Windows (séparateurs) | OK via `pathlib` mais valider la résolution relative au `project_root` partout ; éviter les `Path` littéraux globaux | S |
| **P-13** | 6 | Pas de **préflight** de disponibilité des outils (claude, npx, gh, uv, git, copier) | `harness/resolve.py:20-52` (which pour claude/gh seulement) | compléter | 🟡 | toutes | Préflight qui vérifie via `shutil.which` **tous** les outils requis par le profil/provider retenu, message actionnable | S |

---

## Synthèse par patron d'abstraction (chantiers centralisés)

Cinq chantiers ferment l'essentiel du backlog :

1. **`ProcessRunner` cross-platform unique** (P-07) → ferme **P-01, P-02, P-08** et prévient toute
   régression future. Règle : args en `list[str]`, binaire résolu par `shutil.which`, timeout,
   `shell=False` ; `shell=True` interdit dès que la commande contient une entrée non maîtrisée.
2. **Sélection de profil pilotée par `detect_stack`** (P-03) → ferme **P-03, P-06** et débloque la
   baseline pour les stacks non-Python.
3. **`TargetProfile` enrichi & dérivé du repo** (P-09) → ferme **P-09, P-11** ; dérive
   `test/build/lint` depuis les marqueurs réels (scripts `package.json`, `pyproject`, Makefile).
4. **Gates conditionnels aux marqueurs présents** (P-10) → ferme **P-05, P-10** ; do-no-harm :
   un gate sans marqueur → `skip` tracé, jamais échec.
5. **Abstraction `GitProvider`** (P-04) → ferme **P-04** ; découple la forge de GitHub
   (GitHub / Azure DevOps / GitLab), sélection par l'URL du remote.

Transverse : **préflight outils** (P-13) et **audit chemins Windows** (P-12).

## Ordonnancement recommandé

1. **Débloquer Windows tout de suite** (🔴 rapide) : P-07 puis P-01, P-02, P-08 — la forge cesse de
   crasher sur `npx`/`shell`.
2. **Débloquer les stacks non-Python** (🔴/🟠) : P-03, P-06, P-05 — la baseline et les gates
   s'adaptent à la techno détectée.
3. **Débloquer les autres forges Git** (🔴, effort L) : P-04 — indispensable pour Azure DevOps.
4. **Robustesse & complétude** (🟠/🟡) : P-09, P-10, P-11, P-12, P-13.

## Garde-fous (à respecter dans les correctifs)

- **Jamais `shell=True`** avec une commande contenant chemins/paramètres issus de la mission
  (risque d'injection + quoting non portable). Toujours `list[str]` + `shell=False`.
- **Ne pas coder de nouveau défaut Python** : hors profil connu → `skip` tracé, pas `uv run pytest`.
- **Do-no-harm** : un marqueur absent (DESIGN.md, script test) → gate neutralisé et tracé, jamais
  un échec de baseline sur un projet légitime.
