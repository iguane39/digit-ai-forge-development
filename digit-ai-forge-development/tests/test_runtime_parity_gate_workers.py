"""Gate « parité runtime », sous-contrôle 4 (TF-1998) : la date et les drapeaux de compatibilité
d'un Worker Cloudflare.

Un Worker n'a pas d'image : son runtime est la version de `workerd` que choisit sa
`compatibility_date`, et les `compatibility_flags` qui l'accompagnent. Les tests tournent dans
le runtime local de l'intégration Vitest ou du harnais `createTestHarness`. La parité se juge donc
entre la configuration Wrangler SERVIE et la configuration de TEST. Faits lus le 29/10/2026 :

- « At a minimum, the `name`, `main` and `compatibility_date` keys are required to deploy a
  Worker » (Configuration - Wrangler) ;
- `compatibility_date` et `compatibility_flags` sont des clés héritables, qu'un environnement
  `env.<nom>` peut surcharger (même page) ;
- « If no `compatibility_date` is provided, then the test will use the latest locally available
  date », et les options `miniflare` de la configuration de test priment sur la configuration
  Wrangler (Vitest integration, Configuration) ;
- « By default, the test harness loads the top-level Wrangler configuration » (Configure the
  test harness).

Recette DOUBLE SENS : chaque constat a sa fixture rouge, et le remède que son message propose
est joué sur la même fixture et doit passer (TF-1013).
"""

from __future__ import annotations

from pathlib import Path

from conductor.gates.runtime_parity_gate import (
    _jsonc_vers_json,
    check_parite_compatibilite,
    main,
    run_runtime_parity_gate,
)

_WRANGLER_JSONC = """{
  // Projet de démonstration : commentaire de ligne, URL dans une chaîne, virgules finales.
  "$schema": "./node_modules/wrangler/config-schema.json",
  "name": "worker-paritaire",
  "main": "src/index.ts",
  /* bloc de commentaire */
  "compatibility_date": "2026-10-29",
  "compatibility_flags": ["nodejs_compat",],
  "vars": { "API": "https://exemple.invalid//chemin" },
  "env": {
    "production": { "vars": { "API": "https://exemple.invalid/prod" } },
  },
}
"""

_VITEST_PARITAIRE = """import { cloudflareTest } from "@cloudflare/vitest-plugin";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [
    cloudflareTest({
      wrangler: { configPath: "./wrangler.jsonc" },
    }),
  ],
});
"""

_VITEST_SANS_CONFIG = """import { cloudflareTest } from "@cloudflare/vitest-plugin";
import { defineConfig } from "vitest/config";

export default defineConfig({ plugins: [cloudflareTest({})] });
"""

_VITEST_DATE_ANCIENNE = """import { cloudflareTest } from "@cloudflare/vitest-plugin";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [
    cloudflareTest({
      wrangler: { configPath: "./wrangler.jsonc" },
      miniflare: { compatibilityDate: "2025-01-01" },
    }),
  ],
});
"""

_VITEST_DRAPEAUX_VIDES = """import { cloudflareTest } from "@cloudflare/vitest-plugin";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [
    cloudflareTest({
      wrangler: { configPath: "./wrangler.jsonc" },
      miniflare: { compatibilityFlags: [] },
    }),
  ],
});
"""

# Forme d'avant la version 0.13 de @cloudflare/vitest-pool-workers (guide « Migrate from Vitest 3
# to Vitest 4 ») : options sous test.poolOptions.workers. Encore en service chez qui n'a pas migré.
_VITEST_ANCIEN_POOL = """import {
  defineWorkersConfig,
} from "@cloudflare/vitest-pool-workers/config";

export default defineWorkersConfig({
  test: {
    poolOptions: {
      workers: {
        wrangler: { configPath: "./wrangler.toml" },
        miniflare: { compatibilityDate: "2024-01-01" },
      },
    },
  },
});
"""

_WRANGLER_TOML = """name = "worker-toml"
main = "src/index.ts"
compatibility_date = "2026-10-29"
compatibility_flags = ["nodejs_compat"]
"""

_WRANGLER_TOML_SANS_DATE = """name = "worker-toml"
main = "src/index.ts"
"""


def _worker(
    tmp_path: Path,
    *,
    wrangler: str | None = _WRANGLER_JSONC,
    nom_wrangler: str = "wrangler.jsonc",
    vitest: str | None = _VITEST_PARITAIRE,
    fichiers: dict[str, str] | None = None,
) -> Path:
    """Un projet Worker minimal : configuration Wrangler, configuration Vitest, fichiers libres."""
    racine = tmp_path / "worker"
    racine.mkdir()
    if wrangler is not None:
        (racine / nom_wrangler).write_text(wrangler, encoding="utf-8")
    if vitest is not None:
        (racine / "vitest.config.ts").write_text(vitest, encoding="utf-8")
    for relatif, contenu in (fichiers or {}).items():
        chemin = racine / relatif
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(contenu, encoding="utf-8")
    return racine


def _kinds(racine: Path) -> list[str]:
    return [f["kind"] for f in run_runtime_parity_gate(racine).findings if "kind" in f]


# --- Lecture de la configuration ------------------------------------------------------------


def test_jsonc_lu_sans_toucher_aux_chaines() -> None:
    """Les commentaires et virgules finales tombent ; une URL `//` dans une chaîne reste."""
    import json

    donnees = json.loads(_jsonc_vers_json(_WRANGLER_JSONC))
    assert donnees["compatibility_date"] == "2026-10-29"
    assert donnees["compatibility_flags"] == ["nodejs_compat"]
    assert donnees["vars"]["API"] == "https://exemple.invalid//chemin"
    assert json.loads(_jsonc_vers_json('{"a": "x,}", "b": [1, 2,],}')) == {"a": "x,}", "b": [1, 2]}
    # Une chaîne qui finit par une barre oblique inverse échappée (chemin Windows) se referme :
    # la virgule finale qui suit tombe quand même.
    assert json.loads(_jsonc_vers_json('{"c": "x\\\\", "d": [1,],}')) == {"c": "x\\", "d": [1]}


# --- Sens vert --------------------------------------------------------------------------------


def test_sens_vert_worker_paritaire_passe(tmp_path: Path) -> None:
    """Configuration de test qui charge la configuration servie, environnement sans surcharge."""
    verdict = run_runtime_parity_gate(_worker(tmp_path))
    assert verdict.passed is True
    assert [f for f in verdict.findings if "kind" in f] == []
    # Sans Dockerfile, les sous-contrôles 1 à 3 le DISENT, sans échec fabriqué (P-06).
    assert any("Dockerfile" in f.get("skipped", "") for f in verdict.findings)


def test_sans_wrangler_ni_dockerfile_reste_sans_objet(tmp_path: Path) -> None:
    racine = _worker(tmp_path, wrangler=None, vitest=None)
    verdict = run_runtime_parity_gate(racine)
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]
    assert "Wrangler" in verdict.findings[0]["skipped"]


# --- R1 : date absente de la configuration servie ---------------------------------------------


def test_rouge_date_absente_puis_remede(tmp_path: Path) -> None:
    racine = _worker(
        tmp_path, wrangler=_WRANGLER_TOML_SANS_DATE, nom_wrangler="wrangler.toml", vitest=None
    )
    assert _kinds(racine) == ["compat-date-absente"]
    assert main([str(racine)]) == 1
    # Remède proposé par le message : déclarer compatibility_date.
    (racine / "wrangler.toml").write_text(_WRANGLER_TOML, encoding="utf-8")
    assert _kinds(racine) == []
    assert main([str(racine)]) == 0


# --- R2 : configuration de test qui ne nomme ni date ni configuration Wrangler ----------------


def test_rouge_test_date_implicite_puis_remede(tmp_path: Path) -> None:
    racine = _worker(tmp_path, vitest=_VITEST_SANS_CONFIG)
    assert _kinds(racine) == ["compat-test-date-implicite"]
    # Remède proposé : pointer la configuration servie par wrangler.configPath.
    (racine / "vitest.config.ts").write_text(_VITEST_PARITAIRE, encoding="utf-8")
    assert _kinds(racine) == []


def test_date_non_litterale_est_tracee_sans_constat(tmp_path: Path) -> None:
    """Une date posée par une variable n'est pas lue : trace, jamais un constat fabriqué."""
    vitest = _VITEST_SANS_CONFIG.replace(
        "cloudflareTest({})", "cloudflareTest({ miniflare: { compatibilityDate: DATE } })"
    )
    verdict = run_runtime_parity_gate(_worker(tmp_path, vitest=vitest))
    assert [f for f in verdict.findings if "kind" in f] == []
    assert any("non littéral" in f.get("skipped", "") for f in verdict.findings)


# --- R3 et R4 : la configuration de test prime et diverge ------------------------------------


def test_rouge_date_de_test_divergente_puis_remede(tmp_path: Path) -> None:
    racine = _worker(tmp_path, vitest=_VITEST_DATE_ANCIENNE)
    verdict = run_runtime_parity_gate(racine)
    constats = [f for f in verdict.findings if f.get("kind") == "compat-date-disparite"]
    assert len(constats) == 1
    assert "2025-01-01" in constats[0]["issue"] and "2026-10-29" in constats[0]["issue"]
    # Remède proposé : aligner la date de test sur la date servie.
    (racine / "vitest.config.ts").write_text(
        _VITEST_DATE_ANCIENNE.replace("2025-01-01", "2026-10-29"), encoding="utf-8"
    )
    assert _kinds(racine) == []


def test_rouge_drapeaux_de_test_divergents(tmp_path: Path) -> None:
    racine = _worker(tmp_path, vitest=_VITEST_DRAPEAUX_VIDES)
    assert _kinds(racine) == ["compat-flags-disparite"]
    (racine / "vitest.config.ts").write_text(
        _VITEST_DRAPEAUX_VIDES.replace("[]", '["nodejs_compat"]'), encoding="utf-8"
    )
    assert _kinds(racine) == []


def test_rouge_configuration_de_test_distincte_de_la_servie(tmp_path: Path) -> None:
    """`configPath` vers une autre configuration que celle qui sert : ses dates se comparent."""
    vitest = _VITEST_PARITAIRE.replace("./wrangler.jsonc", "./wrangler.test.toml")
    test_toml = _WRANGLER_TOML.replace("2026-10-29", "2026-03-01")
    racine = _worker(tmp_path, vitest=vitest, fichiers={"wrangler.test.toml": test_toml})
    assert _kinds(racine) == ["compat-date-disparite"]


def test_rouge_ancienne_forme_du_pool(tmp_path: Path) -> None:
    """La forme `defineWorkersConfig` d'avant la 0.13 est reconnue comme intégration Workers."""
    racine = _worker(
        tmp_path, wrangler=_WRANGLER_TOML, nom_wrangler="wrangler.toml", vitest=_VITEST_ANCIEN_POOL
    )
    assert _kinds(racine) == ["compat-date-disparite"]


def test_vitest_sans_integration_workers_est_trace(tmp_path: Path) -> None:
    """Des tests Vitest hors du runtime Workers : la parité n'a rien à comparer, et le dit."""
    vitest = 'import { defineConfig } from "vitest/config";\nexport default defineConfig({});\n'
    verdict = run_runtime_parity_gate(_worker(tmp_path, vitest=vitest))
    assert verdict.passed is True
    assert any("intégration Workers" in f.get("skipped", "") for f in verdict.findings)


# --- R5 : un environnement servi sur une autre version du runtime ------------------------------


_ENV_SURCHARGE = _WRANGLER_JSONC.replace(
    '"production": { "vars"',
    '"production": { "compatibility_date": "2026-06-01", "vars"',
)


def test_rouge_environnement_surcharge_puis_remede_heritage(tmp_path: Path) -> None:
    racine = _worker(tmp_path, wrangler=_ENV_SURCHARGE)
    verdict = run_runtime_parity_gate(racine)
    constats = [f for f in verdict.findings if f.get("kind") == "compat-env-disparite"]
    assert len(constats) == 1
    assert "'production'" in constats[0]["issue"] and "2026-06-01" in constats[0]["issue"]
    # Remède A : retirer la surcharge, l'environnement hérite de la racine.
    (racine / "wrangler.jsonc").write_text(_WRANGLER_JSONC, encoding="utf-8")
    assert _kinds(racine) == []


def test_environnement_surcharge_mais_teste_par_le_harnais(tmp_path: Path) -> None:
    """Remède B : un test d'intégration sélectionne l'environnement par `env`."""
    harnais = (
        'import { createTestHarness } from "wrangler";\n'
        "const server = createTestHarness({\n"
        '  workers: [{ configPath: "./wrangler.jsonc", env: "production" }],\n'
        "});\n"
    )
    racine = _worker(
        tmp_path, wrangler=_ENV_SURCHARGE, fichiers={"test/production.test.ts": harnais}
    )
    assert _kinds(racine) == []


def test_drapeaux_surcharges_par_environnement(tmp_path: Path) -> None:
    wrangler = _WRANGLER_TOML + '\n[env.staging]\ncompatibility_flags = ["nodejs_compat_v2"]\n'
    racine = _worker(tmp_path, wrangler=wrangler, nom_wrangler="wrangler.toml", vitest=None)
    assert _kinds(racine) == ["compat-env-disparite"]


# --- Coexistence avec les sous-contrôles 1 à 3 -------------------------------------------------


def test_conteneur_et_worker_sont_juges_ensemble(tmp_path: Path) -> None:
    dockerfile = 'FROM python:3.11-slim\nRUN python -c "import flask"\nCMD []\n'
    racine = _worker(
        tmp_path,
        wrangler=_WRANGLER_TOML_SANS_DATE,
        nom_wrangler="wrangler.toml",
        vitest=None,
        fichiers={"Dockerfile": dockerfile},
    )
    assert _kinds(racine) == ["compat-date-absente"]


def test_configuration_illisible_est_tracee(tmp_path: Path) -> None:
    racine = _worker(tmp_path, wrangler='{ "name": ', vitest=None)
    traces = check_parite_compatibilite(racine)
    assert all("skipped" in f for f in traces)
    assert "illisible" in traces[0]["skipped"]
