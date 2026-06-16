# vendor/bad — bmad-autonomous-development (vendorisé)

> Dépendance **vendorisée au tag** (décision canonique 06 / NFR-2). Mono-contributeur
> → bus factor élevé (risque 3). On épingle, on ne forke pas (décision 01).

| Champ | Valeur |
|---|---|
| Source | https://github.com/stephenleo/bmad-autonomous-development |
| Tag épinglé | **v1.2.0** |
| Licence | MIT (Marie Stephen Leo, 2026) |
| Nature | **Skill Claude Code** (`/bad`) — *pas* un package Python (spike S-1) |

## À vendoriser (contenu de `skills/bad/`)
`SKILL.md` · `assets/module-setup.md` · `references/coordinator/*` · `references/subagents/*`.

## Commande de vendoring (story 0.2 — à exécuter)
```bash
git clone --depth 1 --branch v1.2.0 \
  https://github.com/stephenleo/bmad-autonomous-development /tmp/bad
cp -r /tmp/bad/skills/bad/* vendor/bad/
# consigner le SHA du tag dans vendor/bad/VERSION
```

## Invocation (étape E, Epic 3)
`supervisor.py` invoque le skill `/bad` (harness Claude Code), avec overrides runtime
et **`AUTO_PR_MERGE=false`** (préserve HITL 2). Prérequis : `gh` authentifié +
`GITHUB_PERSONAL_ACCESS_TOKEN`.

> Placeholder : le contenu réel du skill n'est pas encore copié ici. Le test
> d'intégration maître (`tests/test_e2e_master.py`) cassera quand le contrat upstream
> changera (NFR-3, risque 8).
