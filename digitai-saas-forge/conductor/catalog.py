"""Catalogue des 11 briques SaaS du Toolkit (spike S-3 — décodé du dossier fondateur).

Chaque brique porte une décision build/buy par défaut (positions Digit-AI, à arbitrer
selon le contexte client) et des *actions de scaffolding* — des recettes exécutées par
l'étape B dans le dépôt généré. Le conductor ne réimplémente rien : il séquence ces
commandes (décision 01).

Briques de t0 (décision canonique 05) : multi-tenancy, rbac, auth-sso sont greffées par
défaut, coûteuses à rétro-ajouter.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from conductor.contracts import BrickChoice, BrickDecision

# Briques imposées au scaffold par défaut (décision canonique 05).
T0_BRICKS: tuple[str, ...] = ("multi-tenancy", "rbac", "auth-sso")


class BrickAction(BaseModel):
    """Action de greffe portable (P-11) : commande exécutée dans le répertoire d'un RÔLE.

    `role` est résolu par le profil (``roles`` → répertoire, ``pkg_managers`` → gestionnaire).
    Le token littéral ``{pm}`` dans ``args`` est substitué par le gestionnaire du rôle. Un rôle
    absent du profil → action **non applicable** (skip tracé au scaffold). Plus de ``cd … && …``.
    """

    role: str
    args: list[str]


class BrickSpec(BaseModel):
    """Spécification d'une brique : décision par défaut + recettes de scaffolding."""

    name: str
    default_decision: BrickDecision
    resource: str  # librairie / service de référence
    actions: list[BrickAction] = Field(default_factory=list)  # actions par rôle (P-11)
    t0: bool = False  # greffée par défaut au scaffold (décision 05)


# Source : Toolkit SaaS, 11 briques (spike S-3 §S-3.2). Actions par rôle (P-11) : `{pm}` = le
# gestionnaire du rôle (backend → uv, frontend → npm), résolu par le profil au scaffold.
CATALOG: dict[str, BrickSpec] = {
    "auth-sso": BrickSpec(
        name="auth-sso",
        default_decision="build",
        resource="Authlib (build) ; WorkOS si SSO entreprise",
        actions=[BrickAction(role="backend", args=["{pm}", "add", "authlib"])],
        t0=True,
    ),
    "rbac": BrickSpec(
        name="rbac",
        default_decision="build",
        resource="Casbin",
        actions=[BrickAction(role="backend", args=["{pm}", "add", "casbin"])],
        t0=True,
    ),
    "multi-tenancy": BrickSpec(
        name="multi-tenancy",
        default_decision="build",
        resource="tenant_id row-level (Organization + organization_id)",
        actions=[
            BrickAction(
                role="backend",
                args=["alembic", "revision", "--autogenerate", "-m", "add tenancy"],
            ),
        ],
        t0=True,
    ),
    "billing": BrickSpec(
        name="billing",
        default_decision="buy",
        resource="Stripe (Polar.sh/Lemon Squeezy si TVA UE)",
        actions=[BrickAction(role="backend", args=["{pm}", "add", "stripe"])],
    ),
    "observability": BrickSpec(
        name="observability",
        default_decision="build",
        resource="OpenTelemetry (build) ; Grafana (buy)",
        actions=[
            BrickAction(
                role="backend",
                args=["{pm}", "add", "opentelemetry-sdk", "opentelemetry-instrumentation-fastapi"],
            )
        ],
    ),
    "analytics": BrickSpec(
        name="analytics",
        default_decision="buy",
        resource="PostHog (buy / self-host)",
        actions=[BrickAction(role="frontend", args=["{pm}", "i", "posthog-js"])],
    ),
    "feature-flags": BrickSpec(
        name="feature-flags",
        default_decision="build",
        resource="OpenFeature SDK + Unleash (self-host)",
        actions=[BrickAction(role="backend", args=["{pm}", "add", "openfeature-sdk"])],
    ),
    "crud-api": BrickSpec(
        name="crud-api",
        default_decision="build",
        resource="FastAPI + SQLModel (couvert nativement par le template)",
        actions=[],  # déjà fourni par le template
    ),
    "emailing": BrickSpec(
        name="emailing",
        default_decision="buy",
        resource="Resend + react-email (natif : SMTP + MJML)",
        actions=[
            BrickAction(
                role="frontend",
                args=["{pm}", "i", "react-email", "@react-email/components"],
            )
        ],
    ),
    "jobs-async": BrickSpec(
        name="jobs-async",
        default_decision="build",
        resource="ARQ + Redis (build) ; Inngest si orchestration",
        actions=[BrickAction(role="backend", args=["{pm}", "add", "arq"])],
    ),
    "dashboards": BrickSpec(
        name="dashboards",
        default_decision="build",
        resource="Recharts + endpoints d'agrégation ; Metabase (buy)",
        actions=[BrickAction(role="frontend", args=["{pm}", "i", "recharts"])],
    ),
}


def resolve_bricks(scope: list[BrickChoice]) -> list[BrickSpec]:
    """Sélection finale des briques à greffer, dans un ordre déterministe.

    - Les briques de t0 sont TOUJOURS incluses en `build` (décision 05), même absentes
      du scope ou marquées `skip`.
    - Les autres briques sont incluses si choisies avec une décision != `skip`.
    Les t0 d'abord (auth/rbac/tenancy structurants), puis les autres dans l'ordre du scope.
    """
    chosen: dict[str, BrickSpec] = {}

    # 1. t0 forcées
    for name in T0_BRICKS:
        chosen[name] = CATALOG[name]

    # 2. briques additionnelles non-skip
    for choice in scope:
        if choice.name in T0_BRICKS:
            continue  # déjà forcée, non désactivable
        if choice.decision == "skip":
            continue
        spec = CATALOG.get(choice.name)
        if spec is not None:
            chosen[choice.name] = spec

    # ordre : t0 d'abord, puis l'ordre d'apparition dans le scope
    ordered = [chosen[n] for n in T0_BRICKS]
    for choice in scope:
        if choice.name not in T0_BRICKS and choice.name in chosen:
            ordered.append(chosen[choice.name])
    return ordered
