# Prompt — Résolution de profil générique (« toute techno ») pour digit-ai-saas-forge

> **Destinataire** : le projet `digit-ai-saas-forge` (mainteneur ou son propre conductor en run brownfield `complement`).
> **Objet** : généraliser l'onramp brownfield pour qu'il accepte **n'importe quelle stack** via une **résolution de profil en cascade**, au lieu d'énumérer une techno de plus (fastapi, node-ts, …).
> **Statut** : prêt à implémenter dans la prochaine version. Conventions du repo : Python ≥ 3.11, pydantic, ruff + mypy strict, pytest, français, décisions `DE-N` / portabilité `P-NN` (dernier = `P-13`).

---

## 1. Contexte & problème (constaté dans le code au commit courant)

La Forge sépare déjà **moteur** (gates, sprint, supervision) et **contrat de stack** (`TargetProfile`). Le moteur est piloté par contrat : `conductor/gates/code_gate.py` exécute `profile.code_check`, le scaffold résout `profile.roles` / `profile.pkg_managers`, etc. **C'est un acquis à préserver.**

Ce qui **n'est pas générique** — 3 points d'entrée codés en dur :

1. `conductor/onramp/detect.py` · `detect_stack(repo)` → `Literal["fastapi","node-ts","unknown"]`, par **marqueur racine** seulement (`pyproject.toml` → fastapi ; `package.json` → node-ts ; sinon `unknown`).
2. `conductor/profiles.py` · registre statique `_PROFILES = {"fastapi": FASTAPI_SAAS, "node-ts": NODE_TS}` + `profile_for_stack(stack)`.
3. `conductor/onramp/__init__.py` · `select_onramp(mission)` : `fastapi` → `NoOnramp`/`AdapterOnramp` ; `node-ts` → `BuilderOnramp` ; **sinon `raise ValueError("Stack non supportée … ni FastAPI ni node-ts")`**.

Conséquence : `BuilderOnramp` (la bretelle **générique** non-FastAPI, epic « BB », qui sait *synthétiser un profil, normaliser vers le contrat, capturer la baseline via `code_check`, déclarer la dégradation*) **n'est jamais atteinte** pour une stack inconnue — l'erreur tombe avant. Un repo full-stack sans marqueur racine (ex. backend Flask via `requirements.txt` + frontend React dans `frontend/` + IaC Terraform) est rejeté d'emblée.

**Cas de référence** (à faire passer) : repo brownfield multi-rôles, **backend Python non-FastAPI** (Flask) dans `backend/`, **frontend** dans `frontend/`, **aucun** `pyproject.toml`/`package.json` à la racine.

---

## 2. Objectif

Rendre **générique la _résolution_ du profil**, pas ajouter une techno : *fabriquer un `TargetProfile` valable pour n'importe quel repo*, par **déclaration** ou **inférence**, puis router vers `BuilderOnramp`. Résultat attendu : **plus jamais de « stack non supportée »** pour un repo analysable ; la richesse des profils curés (catalogue de briques) reste un bonus, pas un prérequis.

Slogan d'architecture : **le moteur ne connaît pas la techno — il exige que la techno soit décrite par le contrat.**

---

## 3. Décisions à acter (à consigner dans `docs/decisions-execution.md`)

- **P-14 — Résolution de profil en cascade.** L'onramp brownfield résout le `TargetProfile` par ordre de priorité : ① **manifeste** repo → ② **profil curé** (marqueur) → ③ **inférence heuristique** → ④ **analyse LLM** (opt-in). Le premier qui répond gagne. Aucune stack analysable n'échoue à l'onramp.
- **P-15 — `generic` remplace l'échec.** `detect_stack` ne lève plus indirectement : les stacks non curées sont classées `"generic"` et routées vers `BuilderOnramp` avec le profil résolu. Erreur **seulement** si le repo n'expose **aucun** signal exploitable (ni manifeste, ni gestionnaire de paquets, ni commande) — message actionnable.
- **P-16 — Contrat par rôle.** Les commandes (`test`/`build`/`lint`) et gestionnaires de paquets peuvent être **définis par rôle** (backend/frontend/…), pour les monorepos multi-stack. Compatible avec `roles` existant (P-11).
- **P-17 — HITL-0 valide le profil résolu.** Tout profil **inféré ou déclaré** (③④ et ①) passe par HITL-0 avant le dev : l'humain confirme les commandes/rôles/UI. Dégradation déclarée (catalogue de briques vide) inchangée pour le générique.
- **P-18 — Manifeste opposable prioritaire.** Un `.forge/profile.toml` présent **prime** toute détection : source de vérité explicite, versionnée, revue.

---

## 4. Spécification fonctionnelle

### 4.1 Cascade de résolution `resolve_profile(repo) -> TargetProfile`

1. **① Manifeste** `.forge/profile.toml` (ou `forge.yaml`) présent → `TargetProfile.from_manifest(...)`. **Déterministe, prioritaire (P-18).**
2. **② Curé** : `detect_stack` reconnaît un marqueur curé (`fastapi`, `node-ts`) → profil du registre `_PROFILES`. **Chemin actuel inchangé.**
3. **③ Inférence heuristique** : `synthesize_profile(repo)` à partir des **capacités** détectées (cf. 4.3). Aucune dépendance réseau.
4. **④ Analyse LLM** (opt-in `CONDUCTOR_USE_CLAUDE_ANALYZER=1`, harness `conductor/harness`) : `analyze_profile_with_claude(repo)` si l'heuristique est incomplète (ex. commandes indéterminées). Complète/valide le profil synthétisé.

Le profil résolu porte un **niveau de confiance** (`curated` / `manifest` / `inferred` / `analyzed`) journalisé et affiché au HITL-0.

### 4.2 Routage `select_onramp`

- `greenfield` → `ScaffoldOnramp` (inchangé).
- `brownfield` :
  - `fastapi` → `NoOnramp` (distance A) / `AdapterOnramp` (distance C) — **inchangé**.
  - `node-ts` → `BuilderOnramp(profile=NODE_TS)` — **inchangé**.
  - **sinon** → `BuilderOnramp(profile=resolve_profile(repo))` — **NOUVEAU** (plus de `raise`).
- Erreur explicite uniquement si `resolve_profile` ne trouve **aucun** signal (repo vide/opaque) : message P-15 + comment fournir un `.forge/profile.toml`.

### 4.3 Détection de capacités (heuristique, multi-écosystèmes)

`detect_capabilities(repo) -> Capabilities` scanne des **faits durs** (déterministes), à la racine **et par rôle** (sous-répertoires) :

- Gestionnaires de paquets / stacks : `requirements.txt`, `pyproject.toml`, `poetry.lock`, `package.json`, `go.mod`, `pom.xml`/`build.gradle`, `Cargo.toml`, `composer.json`, `*.csproj`/`*.sln`, `Gemfile`.
- Frameworks de test : pytest (`tests/`, `pytest` en dép), jest/vitest (`package.json` scripts), `go test`, JUnit (maven/gradle), etc.
- Orchestrateurs de commandes : `Makefile`, `justfile`, scripts `package.json`, `tox.ini`.
- CI existante : `.github/workflows/*.yml`, `azure-pipelines.yml`, `.gitlab-ci.yml` (source de commandes fiables).
- **UI** (`has_ui`) : présence d'un front (`frontend/`, `package.json` avec React/Vue/Svelte/Angular, `index.html`).
- **Rôles** : mapping rôle→répertoire déduit (`backend/`, `frontend/`, `api/`, `web/`, `app/`, racine).

`synthesize_profile` transforme ces capacités en `TargetProfile` (commandes par rôle, `has_ui`, `roles`, `pkg_managers`), `brick_catalog={}` (dégradation), `code_check` = commande de test primaire (ou `None` si indéterminée → gate code **skip tracé**, comportement P-06 existant).

### 4.4 HITL-0 (P-17)

`BuilderOnramp` déclare la dégradation **et** joint le profil résolu (niveau de confiance + commandes/rôles). `require_hitl0("normalisation & profil résolu", substrate)` reste le point d'arrêt : l'humain valide/corrige le contrat avant tout dev. En mode `unattended`, HITL-0 reste un **gate de gouvernance** (non contourné).

---

## 5. Spécification technique (fichier par fichier)

| Fichier | Changement |
|---|---|
| `conductor/profiles.py` | + `TargetProfile.from_manifest(path: Path) -> TargetProfile` (parse `.forge/profile.toml`). + `synthesize_profile(repo: Path, caps: Capabilities) -> TargetProfile`. + `resolve_profile(repo: Path) -> ProfileResolution` (cascade P-14, avec `confidence: Literal["curated","manifest","inferred","analyzed"]`). Étendre `TargetProfile` : commandes **par rôle** optionnelles (`commands: dict[str, RoleCommands]` où `RoleCommands = {test,build,lint}`), rétro-compatibles avec `code_check`/`test_cmd`/… (P-16). Conserver `enforceable`. |
| `conductor/onramp/detect.py` | + `detect_capabilities(repo: Path) -> Capabilities` (4.3). `detect_stack` : garder `fastapi`/`node-ts`, renvoyer `"generic"` au lieu de laisser `select_onramp` lever (P-15). `detect_distance` inchangé (fastapi only). |
| `conductor/onramp/__init__.py` | `select_onramp` : cas `generic` → `BuilderOnramp(profile=resolve_profile(repo).profile)`. `raise` seulement si aucun signal. |
| `conductor/onramp/builder_onramp.py` | Accepter un **profil injecté** (au lieu d'appeler seulement `profile_for_stack(stack)`) : `BuilderOnramp(profile: TargetProfile | None = None)` ; si `None`, comportement actuel (node-ts). Joindre le profil résolu + `confidence` au `Substrate` pour HITL-0. |
| `conductor/harness/` (opt-in ④) | + `analyze_profile_with_claude(repo) -> TargetProfile` derrière `CONDUCTOR_USE_CLAUDE_ANALYZER=1` (réutilise `harness/claude_cli.py`, timeout `CONDUCTOR_CLAUDE_TIMEOUT_S`). Prompt : « propose commandes test/build/lint par rôle + has_ui + roles à partir de cet arbre ». Sortie validée pydantic. |
| `conductor/onramp/base.py` | `Substrate` : + `profile_confidence` (et déjà `declared_degradation`). |
| `docs/` | MAJ `run-playbook.md` (+ 5 traductions) et `conductor-run-playbook.*` : matrice de contexte « Externe » → **stack quelconque via résolution générique** ; documenter le manifeste `.forge/profile.toml`. |
| `docs/decisions-execution.md` | Ajouter P-14…P-18. |

### 5.1 Schéma du manifeste `.forge/profile.toml`

```toml
name = "flask-react"        # libellé du profil
has_ui = true               # le gate design s'applique-t-il ?
design_md_path = "design/DESIGN.md"

[roles]                     # rôle -> répertoire (P-11)
backend  = "backend"
frontend = "frontend"

[pkg_managers]              # rôle -> gestionnaire
backend  = "pip"
frontend = "npm"

[commands.backend]          # commandes par rôle (P-16) ; toute clé absente = non applicable (skip tracé)
test = "pytest"
lint = "ruff check ."

[commands.frontend]
test  = "npm test"
build = "npm run build"
lint  = "npm run lint"
```

Règles de validation (pydantic) : `name` requis ; au moins un rôle ; commandes en liste d'arguments sûre (`shlex.split`, jamais `shell=True` — cohérent `code_gate.py`) ; chemins relatifs.

---

## 6. Invariants & non-régression (NE PAS casser)

- **Profils curés inchangés** : `fastapi` (NoOnramp/AdapterOnramp, catalogue de briques complet) et `node-ts` (BuilderOnramp) se comportent **exactement** comme avant. Tests existants verts.
- **Moteur piloté par contrat inchangé** : `code_gate`, sprint, scaffold lisent le profil comme aujourd'hui ; le générique ne fait que **fournir** un profil.
- **Gouvernance préservée** : double gate, non-régression, gate spec (`CONDUCTOR_ENABLE_SPEC_REVIEW`), 2 HITL produit, HITL-0, revue finale, `auto_pr_merge=false`. Le générique **ajoute** HITL-0 sur le profil résolu (P-17), ne retire rien.
- **P-06 conservé** : aucun défaut Python implicite — si `code_check`/commande de rôle indéterminée → gate **skip tracé**, jamais un `pytest` supposé.
- **Déterminisme heuristique** : ③ sans réseau ; ④ opt-in seulement.

---

## 7. Critères d'acceptation (tests pytest à ajouter)

1. **Repo full-stack non-FastAPI (cas de référence)** : backend Flask (`backend/requirements.txt` avec `flask`) + `frontend/package.json`, pas de marqueur racine → `detect_stack == "generic"` ; `select_onramp` renvoie `BuilderOnramp` (ne lève pas) ; `resolve_profile` synthétise un profil `has_ui=true`, `roles={backend,frontend}`, `commands.backend.test` déduit ; `Substrate.declared_degradation is True` ; HITL-0 déclenché (`HitlPending` en headless).
2. **Manifeste prioritaire (P-18)** : un `.forge/profile.toml` présent l'emporte sur l'inférence ; `confidence == "manifest"`.
3. **Curés intacts** : repo FastAPI (pyproject) → NoOnramp/AdapterOnramp selon distance ; repo node-ts → BuilderOnramp(NODE_TS). Aucune régression.
4. **Commandes par rôle (P-16)** : `code_gate` exécute la bonne commande par rôle ; rôle sans commande → skip tracé (P-06).
5. **Repo opaque** : dossier sans aucun signal → erreur explicite P-15 mentionnant `.forge/profile.toml` (pas un traceback nu).
6. **Analyse LLM (④)** : avec `CONDUCTOR_USE_CLAUDE_ANALYZER=1` et un fake runner, `analyze_profile_with_claude` complète le profil ; sans la variable, ③ seul.
7. **HITL-0 profil (P-17)** : profil `inferred`/`analyzed`/`manifest` → HITL-0 requis ; profil `curated` fastapi distance A → pas de HITL-0 (comportement actuel).

---

## 8. Cas limites à traiter

- **Multi-langage backend** (ex. Python + Go) : choisir le rôle primaire par heuristique (répertoire dominant / manifeste) ; documenter le tie-break.
- **Monorepo à N rôles** (> 2) : `roles`/`commands` en dict ouvert — pas de limite à 2.
- **Commandes issues de la CI** : préférer les commandes trouvées dans `azure-pipelines.yml`/workflows GitHub aux devinettes (source fiable).
- **Windows / Azure DevOps** : compatible avec le shim `gh` existant (`harness/gh_shim`) ; ne présumer ni bash ni GitHub.
- **`has_ui` faux positif/négatif** : validable/corrigeable au HITL-0.

---

## 9. Hors périmètre (ne pas tenter)

- **Catalogue de briques de scaffold** pour stacks arbitraires (le générique reste en **dégradation déclarée** : catalogue vide, harness fourni par le repo). Le scaffolding riche demeure l'apanage des profils curés.
- **Remédiation infra/IaC** (Terraform, Azure) et **conformité RGPD/gouvernance** : hors du moteur code, générique ou non.
- Réécriture du moteur de gates : il est déjà contract-driven, on n'y touche pas.

---

## 10. Livrables & process

- Branche `run/<slug>` ; décisions P-14…P-18 dans `docs/decisions-execution.md` ; profils/onramp/detect modifiés ; tests des §7 verts ; `ruff` + `mypy --strict` + `pytest` verts (double gate).
- MAJ documentaire : `docs/run-playbook.md` + 5 traductions, `docs/conductor-run-playbook.*` (matrice « Externe » = stack quelconque), section « Manifeste `.forge/profile.toml` ».
- **PR** vers `iguane39/digit-ai-saas-forge`, `auto_pr_merge=false`, revue humaine avant merge `main` (invariant du playbook).
- Démonstration : un `conductor run "<objectif>" --mode brownfield --repo <repo-full-stack-non-fastapi> --intent remediation` **passe désormais l'onramp** (BuilderOnramp + HITL-0), là où il levait « stack non supportée ».

---

## 11. Definition of Done

- [ ] Un repo brownfield **de stack arbitraire mais analysable** (ou muni d'un `.forge/profile.toml`) est onrampé sans échec, en `BuilderOnramp`, avec HITL-0 sur le profil résolu.
- [ ] Cascade ①②③(④) implémentée, avec `confidence` journalisé.
- [ ] Commandes par rôle (P-16) opérationnelles dans le double gate.
- [ ] Zéro régression sur fastapi/node-ts (suite existante verte).
- [ ] Docs + décisions + PR livrés ; message d'erreur P-15 actionnable pour les repos opaques.
