# Registre des mutants équivalents — mutation gate (TF-0103.2 / TF-0120)

Source unique des mutants jugés **équivalents ou non discriminants** sur le scope
`only_mutate` de `[tool.mutmut]` (`conductor/sandbox.py` + `conductor/gates/ai_antipatterns_gate.py`).
Un mutant listé ici n'a **jamais été exclu** de la mesure (`only_mutate`/`mutmut.toml` inchangés,
aucun `# pragma: no mutate`) : il est mesuré, compté comme survivant dans le score officiel, et
justifié individuellement ou par classe ci-dessous — conformément à la règle « jamais en silence ».

Mesure de référence (Docker, `python:3.11-slim`, mutmut 3.7.0, 12/08/2026, après renforcement
des tests TF-0120) : **344 killed / 21 survived / 365 total → 94,25 %**, dont les 21 survivants
sont exactement les mutants listés ici. Score hors équivalents documentés (dénominateur réduit
aux mutants qui pourraient en principe être tués) : 344/344 = 100 % — tous les survivants
restants sont couverts par une justification ci-dessous.

## Méthode

Chaque mutant a été rejoué individuellement (`uv run mutmut show <id>`), son diff lu, et une
tentative de test discriminant a été écrite. Un mutant n'entre dans ce registre qu'après échec
documenté de cette tentative — jamais par défaut de temps.

## Classe A — nom d'encodage insensible à la casse (`"utf-8"` vs `"UTF-8"`)

Les noms de codec Python sont normalisés (minuscules, tirets/underscores interchangeables) par
`codecs.lookup` avant résolution : `"utf-8"` et `"UTF-8"` désignent strictement le même codec.
Aucune entrée ni sortie observable ne peut distinguer les deux — le mutant est équivalent par
construction du langage, pas par manque d'effort de test.

Mutants : `sandbox.x__cgroup_indicates_container__mutmut_7`,
`ai_antipatterns_gate.x_manifest_import_names__mutmut_5`,
`ai_antipatterns_gate.x_check_missing_dependencies__mutmut_30`,
`ai_antipatterns_gate.x_check_hardcoded_secrets__mutmut_16`,
`ai_antipatterns_gate.x_check_routes_without_auth__mutmut_16`.

## Classe B — encodage par défaut de la locale, indiscernable en environnement CI/devcontainer

Mutants qui suppriment le paramètre `encoding="utf-8"` (`encoding=None` ou paramètre omis),
faisant retomber `Path.read_text()` sur l'encodage de la locale du système. Ce gate ne s'exécute
que sous Docker (`python:3.11-slim`), devcontainer ou WSL (jamais nativement sous Windows — cf.
docstring de `mutation_gate.py`), environnements dont la locale par défaut est UTF-8. Pour tout
contenu ASCII ou UTF-8 valide (le seul testable de façon reproductible et portable), le résultat
est identique avec ou sans le paramètre explicite. Une différence n'existerait que sur un poste
dont la locale n'est PAS UTF-8 — hors du périmètre d'exécution documenté de ce gate — et serait de
toute façon non reproductible en CI (`ubuntu-latest`, locale UTF-8 par défaut).

Mutants : `sandbox.x__cgroup_indicates_container__mutmut_2` (et `_mutmut_4`, paramètre omis),
`ai_antipatterns_gate.x_manifest_import_names__mutmut_3`,
`ai_antipatterns_gate.x_check_missing_dependencies__mutmut_25` (et `_mutmut_27`, paramètre omis),
`ai_antipatterns_gate.x_check_hardcoded_secrets__mutmut_11` (et `_mutmut_13`, paramètre omis),
`ai_antipatterns_gate.x_check_routes_without_auth__mutmut_11` (et `_mutmut_13`, paramètre omis).

Note : le paramètre `errors="ignore"` de ces mêmes appels, lui, N'EST PAS équivalent — sa
mutation (`errors=None`, orthographe altérée) est une vraie régression testée et tuée par des
fixtures dédiées (octets non-UTF-8 injectés dans le fichier scanné, ex.
`tests/test_ai_antipatterns_gate.py::test_missing_dependencies_ignore_octets_invalides`,
`test_hardcoded_secrets_ignore_octets_invalides`, `test_routes_ignore_octets_invalides`,
`test_sandbox.py::test_cgroup_octets_non_utf8_ignores`). Seul le paramètre `encoding` de cette
classe est équivalent, pas l'appel dans son ensemble.

## Classe C — paramètre `filename=` d'`ast.parse` jamais observé

`ast.parse(text, filename=str(path))` n'utilise `filename` que pour l'attribut interne d'une
éventuelle `SyntaxError` — immédiatement avalée par `except SyntaxError: continue` dans
`check_missing_dependencies`. Aucune valeur ne dépend de ce paramètre côté API publique
(`check_missing_dependencies` ne renvoie jamais le contenu d'une `SyntaxError`) : le muter
(`filename=str(None)` ou paramètre omis) ne change aucun comportement observable.

Mutants : `ai_antipatterns_gate.x_check_missing_dependencies__mutmut_24` (paramètre omis),
`ai_antipatterns_gate.x_check_missing_dependencies__mutmut_33` (`filename=str(None)`).

## Classe D — `sys.stdlib_module_names` couvre déjà `"__future__"`

`check_missing_dependencies` construit `allowed = set(sys.stdlib_module_names) | {"__future__"}
| manifest_import_names(...)`. Or `"__future__"` fait partie de `sys.stdlib_module_names` sur
Python 3.11 (c'est un vrai module de la bibliothèque standard) : l'ajout explicite est
**redondant** avec l'union précédente. Muter le littéral (`"XX__future__XX"`, `"__FUTURE__"`)
ne retire jamais `"__future__"` du jeu `allowed`, qui reste présent via `stdlib_module_names`
quel que soit le contenu de ce second opérande — aucun test, quel qu'il soit, ne peut
distinguer les deux.

Mutants : `ai_antipatterns_gate.x_check_missing_dependencies__mutmut_5`,
`ai_antipatterns_gate.x_check_missing_dependencies__mutmut_6`.

## Classe E — gardes `not spec` / `startswith("#")` redondants avec l'échec naturel de la regex

`_dep_name` teste `not spec or spec.startswith("#") or "://" in spec or spec.startswith("git+")`
avant de tenter `_DEP_NAME_RE.match(spec)`, où
`_DEP_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")` exige un premier caractère
alphanumérique après espaces éventuels.

- `not spec` (mutmut_4, `or`→`and`) : la seule valeur pour laquelle `not spec` est vrai après
  `.strip()` est la chaîne vide `""`. Or `_DEP_NAME_RE.match("")` échoue déjà naturellement
  (aucun caractère à faire correspondre) — la regex renvoie `None` tout aussi bien sans ce
  garde. Le muter ne change donc jamais le résultat final (`None` dans les deux cas).
- `spec.startswith("#")` (mutmut_7, littéral déformé) : un commentaire commence par `#`, qui
  n'est pas alphanumérique — `_DEP_NAME_RE.match(spec)` échoue déjà naturellement sur toute
  chaîne commençant par `#`. Même conclusion : le garde est une optimisation de lisibilité
  (évite l'appel regex), pas une branche qui change le résultat observable.

Ces deux gardes restent une bonne pratique de code (clarté d'intention, court-circuit avant
regex) mais sont mathématiquement redondants avec le comportement de `_DEP_NAME_RE` pour
CETTE implémentation précise — aucun test ne peut les rendre discriminants sans changer la
regex elle-même (hors périmètre de cet item).

Mutants : `ai_antipatterns_gate.x__dep_name__mutmut_4`, `ai_antipatterns_gate.x__dep_name__mutmut_7`.

## Classe F — `findings = ...` vs `findings += ...` sur liste garantie vide

Dans `run_ai_antipatterns_gate`, la toute première écriture dans `findings` après son
initialisation (`findings: list[dict[str, str]] = []`) est
`findings += check_missing_dependencies(...)` (branche pyproject présent) ou
`findings.append(...)` (branche absente) — aucune des deux branches n'accumule dans une liste
déjà peuplée. Remplacer ce premier `+=` par `=` produit donc exactement le même contenu
(`[] += x == [] = x` pour toute liste `x`) : le mutant est équivalent tant que cette ligne reste
la première écriture — un test qui romprait cette hypothèse (ajouter un append avant) changerait
la nature du code, pas seulement du test.

Mutant : `ai_antipatterns_gate.x_run_ai_antipatterns_gate__mutmut_16`.

## Total

| Classe | Compte |
|---|---|
| A — casse d'encodage | 5 |
| B — encodage locale (CI = UTF-8) | 9 |
| C — `filename=` non observé | 2 |
| D — `__future__` redondant avec stdlib | 2 |
| E — gardes redondants avec la regex | 2 |
| F — `=`/`+=` sur liste vide | 1 |
| **Total documenté** | **21** |

Ce total de 21 correspond exactement aux 21 survivants de la mesure de référence ci-dessus —
aucun survivant non classé.

Historique : première mesure réelle 12/08/2026 — 223/142/365 (61,1 %), sous le seuil documenté
de `conductor/gates/mutation_gate.py`. Après renforcement des tests (TF-0120, même jour) :
344/21/365 (94,25 %) — seuil 75 % dépassé, y compris SANS retirer les 21 mutants documentés du
dénominateur. Le job CI `mutation` (`.github/workflows/double-gate.yml`) est en conséquence
passé de `continue-on-error: true` à bloquant.
