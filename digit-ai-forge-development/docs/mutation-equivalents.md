# Registre des mutants équivalents — mutation gate (TF-0103.2 / TF-0120 / TF-2068)

Source unique des mutants jugés **équivalents** sur le scope `only_mutate` de `[tool.mutmut]`
(`conductor/sandbox.py` + `conductor/gates/ai_antipatterns_gate.py`).
Un mutant listé ici n'a **jamais été exclu** de la mesure (`only_mutate`/`mutmut.toml` inchangés,
aucun `# pragma: no mutate`) : il est mesuré, compté comme survivant dans le score officiel, et
justifié individuellement ou par classe ci-dessous — conformément à la règle « jamais en silence ».

Mesure de référence (Docker, `python:3.11-slim`, mutmut 3.7.0, **03/11/2026**, après les tests de
TF-2068) : **634 killed / 19 survived / 653 total → 97,09 %**, dont les 19 survivants sont
exactement les mutants listés ici. Score hors équivalents documentés (dénominateur réduit aux
mutants qui pourraient en principe être tués) : 634/634 = 100 %. Commandes rejouées, celles du job
`mutation` de `.github/workflows/double-gate.yml` :

```
uv run mutmut run
uv run mutmut export-cicd-stats
uv run python -m conductor.gates.mutation_gate mutants/mutmut-cicd-stats.json
```

## Ce qu'est un mutant équivalent ici

Un mutant est équivalent quand **aucune entrée du programme** ne le distingue de l'original :
arguments, contenu des fichiers lus, variables d'environnement, locale du processus, liste des
modules que l'interpréteur déclare. Un test qui ne le distingue qu'en remplaçant une fonction ou
une constante interne du module, ou en espionnant les arguments d'un appel, éprouve
l'implémentation et non le comportement : cela ne compte pas comme distinction.

## Méthode

Chaque mutant a été rejoué individuellement (`uv run mutmut show <id>`), son diff lu, et une
tentative de test discriminant a été écrite en **variant l'entrée** : octets invalides, locale non
UTF-8, dialecte de chaîne CI, motif hors fenêtre, avertissement du compilateur. Un mutant n'entre
dans ce registre qu'après échec documenté de cette tentative — jamais par défaut de temps. Les
identifiants sont ceux de la mesure du 03/11/2026 : mutmut numérote les mutants par fonction, un
identifiant ne vaut que pour le code qu'il désigne, et le diff de chacun des 19 a été relu à cette
date.

Deux pièges de mesure, relevés le 03/11/2026 :

- mutmut ne relie un test à une fonction que par les appels qu'il observe **dans le processus du
  test**. Un test qui ne joue la fonction que dans un processus fils (cas de la locale ci-dessous)
  ne la couvre pas aux yeux de mutmut et laisse ses mutants vivre. Ces tests appellent donc aussi
  la fonction chez eux, et exigent que le fils rende le même résultat
  (`tests/_locale_ascii.py`).
- une classe « indiscernable » doit nommer l'entrée qui manque. Les anciennes classes B, C et D
  (levées plus bas) affirmaient l'inverse pour une entrée que la suite pouvait fournir.

## Classe A — nom d'encodage insensible à la casse (`"utf-8"` vs `"UTF-8"`)

Les noms de codec Python sont normalisés (minuscules, tirets/underscores interchangeables) par
`codecs.lookup` avant résolution : `"utf-8"` et `"UTF-8"` désignent strictement le même codec.
Aucune entrée ni sortie observable ne peut distinguer les deux — le mutant est équivalent par
construction du langage, pas par manque d'effort de test. Seul un test espion sur l'argument
`encoding` de `Path.read_text` verrait la casse : il vérifierait l'écriture du source, pas un
comportement.

Mutants (11) : `sandbox.x__cgroup_indicates_container__mutmut_7`,
`ai_antipatterns_gate.x_manifest_import_names__mutmut_5`,
`ai_antipatterns_gate.x_check_missing_dependencies__mutmut_30`,
`ai_antipatterns_gate.x_check_hardcoded_secrets__mutmut_16`,
`ai_antipatterns_gate.x_check_routes_without_auth__mutmut_16`,
`ai_antipatterns_gate.x__package_json_quality_scripts__mutmut_10`,
`ai_antipatterns_gate.x__pyproject_linters__mutmut_6`,
`ai_antipatterns_gate.x__pre_commit_hook_ids__mutmut_12`,
`ai_antipatterns_gate.x__chain_text__mutmut_27`,
`ai_antipatterns_gate.x_check_archiving_step_continue_on_error__mutmut_11`,
`ai_antipatterns_gate.x_check_event_wait_after_action__mutmut_18`.

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
CETTE implémentation précise. Aucune chaîne passée à `_dep_name` ne les rend discriminants ;
seul un test qui remplacerait `_DEP_NAME_RE` par une autre regex le ferait, et il éprouverait
l'implémentation (voir la définition ci-dessus).

Mutants (2) : `ai_antipatterns_gate.x__dep_name__mutmut_4`, `ai_antipatterns_gate.x__dep_name__mutmut_7`.

## Classe F — `findings = ...` vs `findings += ...` sur liste garantie vide

Dans `run_ai_antipatterns_gate`, la toute première écriture dans `findings` après son
initialisation (`findings: list[dict[str, str]] = []`) est
`findings += check_missing_dependencies(...)` (branche pyproject présent) ou
`findings.append(...)` (branche absente) — aucune des deux branches n'accumule dans une liste
déjà peuplée. Remplacer ce premier `+=` par `=` produit donc exactement le même contenu
(`[] += x == [] = x` pour toute liste `x`) : le mutant est équivalent tant que cette ligne reste
la première écriture — un test qui romprait cette hypothèse (ajouter un append avant) changerait
la nature du code, pas seulement du test.

Même cas dans `_workflow_files` : `files` vaut `[]` à l'entrée de la branche
`.github/workflows`, première écriture de la liste. Les deux autres `+=` de la fonction (branches
`pipelines/` et `azure-pipelines*`) ne sont PAS dans cette classe : la liste y est déjà peuplée,
leur mutation en `=` est tuée par `test_workflow_files_liste_les_trois_emplacements_dans_l_ordre`.

Mutants (2) : `ai_antipatterns_gate.x_run_ai_antipatterns_gate__mutmut_16`,
`ai_antipatterns_gate.x__workflow_files__mutmut_9`.

## Classe G — défaut de `dict.get` suivi d'un garde de type qui rend la même valeur neutre

`_package_json_quality_scripts` lit `scripts = data.get("scripts", {})` puis rend `{}` si
`scripts` n'est pas un `dict`. Remplacer le défaut `{}` par `None` (mutmut_13) ou le retirer
(mutmut_15, défaut implicite `None`) fait entrer `None` dans le garde de type, qui rend `{}` :
le résultat est `{}` dans les deux cas, pour un `package.json` sans clé `scripts`.
`_pyproject_linters` a la même structure sur `tool = data.get("tool", {})` : défaut `None`
(mutmut_9) ou retiré (mutmut_11) rend `[]` par le garde de type, comme le défaut `{}` rend `[]`
par la compréhension sur un dict vide. Aucun contenu de fichier ne distingue les deux chemins.

Mutants (4) : `ai_antipatterns_gate.x__package_json_quality_scripts__mutmut_13`,
`ai_antipatterns_gate.x__package_json_quality_scripts__mutmut_15`,
`ai_antipatterns_gate.x__pyproject_linters__mutmut_9`,
`ai_antipatterns_gate.x__pyproject_linters__mutmut_11`.

## Total

| Classe | Compte |
|---|---|
| A — casse d'encodage | 11 |
| E — gardes redondants avec la regex | 2 |
| F — `=`/`+=` sur liste vide | 2 |
| G — défaut de `get` absorbé par un garde de type | 4 |
| **Total documenté** | **19** |

Ce total de 19 correspond exactement aux 19 survivants de la mesure de référence ci-dessus —
aucun survivant non classé.

## Classes levées le 03/11/2026 (TF-2068) : des entrées que la suite pouvait fournir

Le registre du 12/08/2026 classait 21 mutants. Treize d'entre eux ont été tués le 03/11 par des
tests qui fournissent l'entrée dont l'ancienne justification niait l'existence. Les classes B, C
et D ne figurent plus au total.

- **Ancienne classe B — encodage par défaut de la locale (9 mutants).** Mutants :
  `sandbox.x__cgroup_indicates_container__mutmut_2` et `_4`,
  `ai_antipatterns_gate.x_manifest_import_names__mutmut_3`,
  `x_check_missing_dependencies__mutmut_25` et `_27`, `x_check_hardcoded_secrets__mutmut_11` et
  `_13`, `x_check_routes_without_auth__mutmut_11` et `_13`. L'argument « la locale de la CI est
  UTF-8 » décrivait la suite, pas le programme : la locale est une entrée du processus, et un
  processus fils lancé avec `LC_ALL=C`, `PYTHONUTF8=0` et `PYTHONCOERCECLOCALE=0` lit en ASCII
  (`locale.getpreferredencoding()` rend `ANSI_X3.4-1968`). Sans `encoding="utf-8"`, un fichier
  UTF-8 s'y lit autrement : `dock` + `é` + `er` devient `docker` sous `errors="ignore"` ; un
  `é` dans un identifiant change le message du constat. Tués par
  `test_cgroup_lu_en_utf8_quelle_que_soit_la_locale`
  (`tests/test_sandbox.py`) et `test_manifest_lu_…`, `test_imports_fantomes_lus_…`,
  `test_secrets_lus_…`, `test_routes_lues_en_utf8_quelle_que_soit_la_locale`
  (`tests/test_ai_antipatterns_gate.py`).
- **Ancienne classe C — `filename=` d'`ast.parse` (2 mutants).** Mutants :
  `x_check_missing_dependencies__mutmut_24` (paramètre omis) et `_33` (`filename=str(None)`).
  `filename` n'est pas muet : l'avertissement du compilateur sur une séquence d'échappement
  invalide (`"\d"`) porte ce nom de fichier (`DeprecationWarning` en 3.11, `SyntaxWarning` dès
  3.12). Omis, l'avertissement dit `<unknown>` ; muté, il dit `None`. Tués par
  `test_missing_dependencies_nomme_le_fichier_dans_les_avertissements_de_syntaxe`.
- **Ancienne classe D — `"__future__"` dans `allowed` (2 mutants).** Mutants :
  `x_check_missing_dependencies__mutmut_5` et `_6`. L'ajout explicite est redondant tant que
  `sys.stdlib_module_names` contient `__future__`, ce qui est vrai en 3.11. La liste des modules
  de l'interpréteur est pourtant une donnée que le programme reçoit : avec une liste qui omet
  `__future__`, `from __future__ import annotations` devient un import fantôme sans l'ajout
  explicite. Tués par `test_missing_dependencies_autorise_future_meme_hors_liste_stdlib`.

## Survivants apparus depuis le 12/08/2026 (72) : 61 tués, 11 classés

Les 72 survivants que la mesure du 02/11/2026 comptait en plus des 21 du 12/08 viennent des
nouvelles fonctions (voir l'historique). 61 sont tués par les tests de TF-2068 :
lectures UTF-8 sous locale ASCII (fonctions `_package_json_quality_scripts`,
`_pyproject_linters`, `_pre_commit_hook_ids`, `_chain_text`, `check_archiving_…`,
`check_event_wait_…`), octets invalides sur les quatre dernières (`errors=None`, littéral
altéré), dialectes de chaîne CI de `_workflow_files` (liste exacte des six emplacements),
`_chain_text` sans dossier et à deux fichiers, `_find_repo_root` au plafond de 5 niveaux,
`pnpm lint` sans le mot `run`, guillemets et lettre `X` en bord d'identifiant de hook,
spécifications sous `node_modules`/`Vendor`/`.venv` et dossier nommé `*.spec.ts`, message
complet du constat d'attente, et ligne imprimée pour un constat sans fichier
(`(chaîne CI)`). Les 11 autres sont classés : 6 en classe A, 4 en classe G, 1 en classe F.

## Historique

Première mesure réelle 12/08/2026 — 223/142/365 (61,1 %), sous le seuil documenté de
`conductor/gates/mutation_gate.py`. Après renforcement des tests (TF-0120, même jour) :
344/21/365 (94,25 %) — seuil 75 % dépassé, y compris SANS retirer les 21 mutants documentés du
dénominateur. Le job CI `mutation` (`.github/workflows/double-gate.yml`) est en conséquence
passé de `continue-on-error: true` à bloquant.

02/11/2026 (TF-2059) : 560/93/653 (85,76 %). Le scope compte 288 mutants de plus que le 12/08,
mesurés le 03/11/2026 par décompte des mutants générés par fonction : le `ai_antipatterns_gate.py`
du 12/08 (commit f0927cd) en génère 332, celui d'aujourd'hui 620, et `sandbox.py`, identique à
f0927cd, en génère 33 dans les deux cas (365 puis 653). Les 288 se répartissent ainsi :

- commit 25e29a4 (14/09/2026, TF-1041, outil de qualité déclaré jamais câblé) : 157 mutants dans
  sept fonctions nouvelles, `_find_repo_root`, `_package_json_quality_scripts`,
  `_pyproject_linters`, `_pre_commit_hook_ids`, `_chain_text`, `_cited_and_wired`,
  `check_declared_tools_not_wired` ;
- commit 79eef0b (15/09/2026, TF-1111 et TF-1112) : 115 mutants dans trois fonctions nouvelles,
  `_workflow_files`, `check_archiving_step_continue_on_error`, `check_event_wait_after_action` ;
- les deux commits ensemble : 16 mutants de plus dans `run_ai_antipatterns_gate` (+9) et `main`
  (+7), qui appellent les contrôles ajoutés et impriment leurs constats.

Les 288 mutants nouveaux portaient 72 survivants et 216 tués (75,0 %), pour 21 survivants sur
365 avant : la baisse de 94,25 % à 85,76 % vient des tests qui n'avaient pas suivi ces deux
commits, pas d'une dégradation des tests d'origine.

03/11/2026 (TF-2068) : rejeu à l'identique (560/93/653), tri des 93 survivants, 26 tests ajoutés
(561 passés au lieu de 535), mesure finale 634/19/653 (97,09 %). Seuil de 75 % inchangé,
`only_mutate` et `pytest_add_cli_args_test_selection` inchangés.
