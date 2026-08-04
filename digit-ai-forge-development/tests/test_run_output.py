"""Sortie machine du run (R-V1) : `_forge-output/run-report.json` + codes de retour.

Un run doit être exploitable par un outil : un fichier JSON dans le repo cible et un code
de retour qui distingue le run complet (0), la pause HITL (2, légitime) et l'erreur (1).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import conductor.__main__ as cli
from conductor.contracts import BadSprintLayout, BmadPlan, SprintReport, StoryResult
from conductor.onramp.base import Substrate
from conductor.profiles import FASTAPI_SAAS
from conductor.report import REPORT_FILE, SystemClock, write_run_report

FROZEN = datetime(2026, 8, 4, 12, 30, 45, tzinfo=UTC)


class FrozenClock:
    """Horloge de test : le rapport ne dépend pas de l'instant d'exécution."""

    def now(self) -> datetime:
        return FROZEN


class _Onramp:
    def __init__(self, degradation: list[str] | None = None) -> None:
        self._degradation = degradation or []

    def prepare(self, config: object, dest: Path) -> Substrate:
        return Substrate(
            repo_path=dest,
            profile=FASTAPI_SAAS,
            design_md_path=dest / "d.md",
            declared_degradation=self._degradation,
        )


def _wire_success(monkeypatch: pytest.MonkeyPatch, report: SprintReport) -> None:
    """Neutralise B→E : le sujet du test est la sortie du run, pas les étapes."""
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
            sprint_status_yaml=root / "status.yaml",
            bmad_config_yaml=root / "config.yaml",
        ),
    )
    monkeypatch.setattr(cli, "superviser", lambda _layout, **_k: report)


def _read_report(target: Path) -> dict[str, object]:
    return dict(json.loads((target / REPORT_FILE).read_text(encoding="utf-8")))


# --- codes de retour ---------------------------------------------------------


def test_run_complet_rend_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _wire_success(monkeypatch, SprintReport())
    assert cli.main(["run", "un CRM pour artisans"]) == cli.EXIT_OK


def test_pause_hitl_rend_deux_et_imprime_la_question(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """HITL-0 non approuvé : pause légitime → code 2, question imprimée en clair."""
    monkeypatch.setattr(cli, "select_onramp", lambda _m: _Onramp(["DESIGN.md créé"]))

    code = cli.main(["run", "assainir", "--mode", "brownfield", "--repo", str(tmp_path)])

    assert code == cli.EXIT_HITL_PENDING
    out = capsys.readouterr().out
    assert "HITL-0" in out
    assert "normalisation & carte d'archi" in out


def test_erreur_rend_un(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    def _boom(_mission: object) -> object:
        raise RuntimeError("onramp indisponible")

    monkeypatch.setattr(cli, "select_onramp", _boom)

    assert cli.main(["run", "une idee"]) == cli.EXIT_ERROR
    assert "onramp indisponible" in capsys.readouterr().err


# --- fichier JSON ------------------------------------------------------------


def test_run_complet_ecrit_le_rapport_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    sprint = SprintReport(
        results=[StoryResult(story_id="1.1", status="ready-for-review", attempts=1)]
    )
    _wire_success(monkeypatch, sprint)

    assert cli.main(["run", "un CRM pour artisans"]) == cli.EXIT_OK

    data = _read_report(tmp_path / "generated" / "un-crm-pour-artisans")
    assert data["status"] == "complete"
    assert data["idea"] == "un CRM pour artisans"
    assert data["mode"] == "greenfield"
    assert data["sprint"] == {
        "results": [
            {"story_id": "1.1", "status": "ready-for-review", "attempts": 1, "pr_url": None}
        ],
        "hitl2_approved": False,
        "merged": False,  # verrouillé (décision 07) : le rapport machine l'expose tel quel
    }


def test_rapport_json_ecrit_aussi_en_pause_hitl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "select_onramp", lambda _m: _Onramp(["DESIGN.md créé"]))

    assert (
        cli.main(["run", "assainir", "--mode", "brownfield", "--repo", str(tmp_path)])
        == cli.EXIT_HITL_PENDING
    )

    data = _read_report(tmp_path)
    assert data["status"] == "hitl-pending"
    assert data["sprint"] is None
    assert "HITL-0" in str(data["detail"])


def test_rapport_json_ecrit_aussi_en_erreur(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    def _boom(_mission: object) -> object:
        raise RuntimeError("onramp indisponible")

    monkeypatch.setattr(cli, "select_onramp", _boom)
    cli.main(["run", "une idee"])

    data = _read_report(tmp_path / "generated" / "une-idee")
    assert data["status"] == "error"
    assert "onramp indisponible" in str(data["detail"])


# --- horloge injectée --------------------------------------------------------


def test_horodatage_injecte(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """L'horloge est injectable : le rapport est reproductible en test."""
    _wire_success(monkeypatch, SprintReport())

    cli.run("une idee", workdir=tmp_path, clock=FrozenClock())

    data = _read_report(tmp_path / "une-idee")
    assert datetime.fromisoformat(str(data["generated_at"])) == FROZEN


def test_horloge_par_defaut_est_aware_utc() -> None:
    assert SystemClock().now().tzinfo is not None


def test_write_run_report_cree_le_dossier_et_rend_le_chemin(tmp_path: Path) -> None:
    dest = write_run_report(
        tmp_path / "repo", status="complete", idea="i", mode="greenfield", clock=FrozenClock()
    )
    assert dest == tmp_path / "repo" / REPORT_FILE
    assert dest.exists()


def test_run_rend_le_sprint_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """run() ne jette plus le bilan : il le renvoie à l'appelant."""
    sprint = SprintReport(results=[StoryResult(story_id="2.1", status="blocked", attempts=4)])
    _wire_success(monkeypatch, sprint)
    assert cli.run("une idee", workdir=tmp_path) is sprint
