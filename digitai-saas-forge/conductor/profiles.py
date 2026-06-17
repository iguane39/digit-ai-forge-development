"""TargetProfile — le contrat d'une stack (gate code, applicabilité design, briques).

Le profil `fastapi-saas` réifie le comportement actuel de la forge (cf. spec brownfield).
`enforceable` décrit la part du contrat applicable — base de la dégradation déclarée (B).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from conductor.catalog import CATALOG, BrickSpec


class TargetProfile(BaseModel):
    name: str
    code_check: str | None  # commande du gate code ; None → gate code non applicable
    has_ui: bool  # le gate design s'applique-t-il ?
    design_md_path: str = "design/DESIGN.md"  # convention RELATIVE (≠ chemin concret du Substrate)
    conventions: str = ""
    brick_catalog: dict[str, BrickSpec] = Field(default_factory=dict)

    @property
    def enforceable(self) -> dict[str, bool]:
        """Part du contrat réellement applicable (gates) pour cette stack."""
        return {"code": self.code_check is not None, "design": self.has_ui}


# Profil canonique = la forge actuelle (FastAPI + React, ruff/mypy/pytest, double gate).
FASTAPI_SAAS = TargetProfile(
    name="fastapi-saas",
    code_check="uv run pytest",
    has_ui=True,
    design_md_path="design/DESIGN.md",
    conventions="ruff + mypy strict; FastAPI + React; scaffold-first; double gate",
    brick_catalog=CATALOG,
)
