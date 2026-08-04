"""Options de cadrage exposées au CLI (R-V5) : --charter, --target, --style, --scope.

`cadrer()` acceptait déjà cible, charte, style et scope SaaS ; le CLI ne les exposait pas.
On vérifie ici le passage effectif à `cadrer()` et la qualité de l'erreur sur un scope invalide
(le CLI ne doit jamais cracher une trace : code 1 + message lisible).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import conductor.__main__ as cli
from conductor.cadrage import cadrer, charger_scope
from conductor.contracts import BadSprintLayout, BmadPlan, MissionConfig, SprintReport
from conductor.onramp.base import Substrate
from conductor.profiles import FASTAPI_SAAS


class _Onramp:
    def prepare(self, config: object, dest: Path) -> Substrate:
        return Substrate(repo_path=dest, profile=FASTAPI_SAAS, design_md_path=dest / "d.md")


def _wire(monkeypatch: pytest.MonkeyPatch) -> dict[str, MissionConfig]:
    """Neutralise B→E et capture la MissionConfig réellement produite par l'étape A."""
    captured: dict[str, MissionConfig] = {}

    def spy(idea: str, **kwargs: object) -> MissionConfig:
        mission = cadrer(idea, **kwargs)  # type: ignore[arg-type]
        captured["mission"] = mission
        return mission

    monkeypatch.setattr(cli, "cadrer", spy)
    monkeypatch.setattr(cli, "select_onramp", lambda _m: _Onramp())
    monkeypatch.setattr(
        cli,
        "lancer_planification",
        lambda substrate, **_k: BmadPlan(
            prd_path=Path("PRD.md"),
            architecture_path=Path("architecture.md"),
            epics_md=Path("epics.md"),
            hitl1_approved=True,
        ),
    )
    monkeypatch.setattr(
        cli,
        "preparer_sprint",
        lambda plan, root, **_k: BadSprintLayout(
            project_root=root,
            epics_md=root / "epics.md",
            sprint_status_yaml=root / "s.yaml",
            bmad_config_yaml=root / "c.yaml",
        ),
    )
    monkeypatch.setattr(cli, "superviser", lambda _layout, **_k: SprintReport())
    return captured


# --- flags de cadrage --------------------------------------------------------


def test_flags_charter_target_style_atteignent_cadrer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    captured = _wire(monkeypatch)

    code = cli.main(
        [
            "run", "une idee",
            "--charter", "brand/CHARTE.md",
            "--target", "node-ts",
            "--style", "acme",
        ]
    )

    assert code == cli.EXIT_OK
    mission = captured["mission"]
    assert mission.brand_charter == Path("brand/CHARTE.md")
    assert mission.target == "node-ts"
    assert mission.style_slug == "acme"


def test_defauts_de_cadrage_inchanges_sans_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    captured = _wire(monkeypatch)

    assert cli.main(["run", "une idee"]) == cli.EXIT_OK

    mission = captured["mission"]
    assert mission.target == "fastapi-saas"
    assert mission.style_slug == "digitai"
    assert mission.brand_charter == Path("design/DESIGN.md")


def test_flag_scope_alimente_le_saas_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scope = tmp_path / "scope.json"
    scope.write_text(
        json.dumps([{"name": "billing", "decision": "buy"}]), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    captured = _wire(monkeypatch)

    assert cli.main(["run", "une idee", "--scope", str(scope)]) == cli.EXIT_OK

    scope_names = {b.name: b.decision for b in captured["mission"].saas_scope}
    assert scope_names["billing"] == "buy"
    assert scope_names["rbac"] == "build"  # briques de t0 toujours forcées (décision 05)


# --- erreurs propres sur --scope ---------------------------------------------


def test_scope_json_malforme_rend_un(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    scope = tmp_path / "scope.json"
    scope.write_text("{ pas du json", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli.main(["run", "une idee", "--scope", str(scope)]) == cli.EXIT_ERROR
    assert "JSON invalide" in capsys.readouterr().err


def test_scope_hors_contrat_rend_un(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`decision` hors du Literal build|buy|skip → rejet par les contrats pydantic."""
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps([{"name": "billing", "decision": "louer"}]), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli.main(["run", "une idee", "--scope", str(scope)]) == cli.EXIT_ERROR
    assert "Scope invalide" in capsys.readouterr().err


def test_scope_introuvable_rend_un(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    assert cli.main(["run", "une idee", "--scope", "absent.json"]) == cli.EXIT_ERROR
    assert "illisible" in capsys.readouterr().err


def test_scope_avec_brique_hors_catalogue_rend_un(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    scope = tmp_path / "scope.json"
    scope.write_text(
        json.dumps([{"name": "quantum-blockchain", "decision": "build"}]), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    assert cli.main(["run", "une idee", "--scope", str(scope)]) == cli.EXIT_ERROR
    assert "inconnue" in capsys.readouterr().err


# --- chargeur de scope (unité) -----------------------------------------------


def test_charger_scope_lit_une_liste_de_briques(tmp_path: Path) -> None:
    scope = tmp_path / "scope.json"
    scope.write_text(
        json.dumps([{"name": "billing", "decision": "buy"}, {"name": "rbac", "decision": "build"}]),
        encoding="utf-8",
    )
    bricks = charger_scope(scope)
    assert [b.name for b in bricks] == ["billing", "rbac"]


def test_charger_scope_refuse_un_objet_racine(tmp_path: Path) -> None:
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps({"billing": "buy"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Scope invalide"):
        charger_scope(scope)
