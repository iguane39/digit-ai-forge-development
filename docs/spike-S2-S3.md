# Spikes S-2 & S-3 — design.md (gate design) + template & Toolkit SaaS

> **Statut : RÉSOLUS.** Sources : audits Digit-AI embarqués (BLOB #3, #4, #6) + dépôts réels `google-labs-code/design.md` et `fastapi/full-stack-fastapi-template` (vérifiés).

---

## S-2 — `design.md@0.3.0` : le gate design est-il viable et bloquant ?

### Réponse
Outil **adoptable tel quel** (npm `@google/design.md`, **Apache 2.0**, stateless, sans réseau, via `npx`). Mais **piège de gating** identifié — voir §S-2.3.

### S-2.1 — CLI réelle (commandes figées)
| Besoin | Commande |
|---|---|
| Lint (humain) | `npx @google/design.md@0.3.0 lint DESIGN.md` |
| Lint (machine) | `npx @google/design.md@0.3.0 lint --format json DESIGN.md` (ou `cat DESIGN.md \| … lint -`) |
| Export Tailwind | `npx @google/design.md@0.3.0 export --format css-tailwind DESIGN.md > theme.css` |
| Export DTCG | `npx @google/design.md@0.3.0 export --format dtcg DESIGN.md > tokens.json` |
| Spec / règles | `npx @google/design.md@0.3.0 spec --rules --format json` |
| Diff | `npx @google/design.md@0.3.0 diff DESIGN.md DESIGN-v2.md` |

### S-2.2 — Les 9 règles de lint
`broken-ref` · `missing-primary` · `contrast-ratio` · `orphaned-tokens` · `token-summary` · `missing-sections` · `missing-typography` · `section-order` · `unknown-key`
→ couvrent les 3 exigences du dossier : **refs non cassées** (`broken-ref`), **contraste WCAG** (`contrast-ratio`), **on-system / structure** (`missing-sections`, `section-order`, `missing-typography`, `unknown-key`).

### S-2.3 — ⚠ PIÈGE CRITIQUE : l'exit code ne suffit pas à bloquer
> Spec : *« Exit code `1` if errors are found, `0` otherwise. »*
> **Mais** : seuls les findings de sévérité `error` forcent l'échec. Les sévérités sont `error | warning | info`, et **il n'existe aucun flag `--strict` documenté**. Le `contrast-ratio` peut être émis en **`warning`** → exit code `0` → **le gate laisserait passer une violation WCAG.**

**Conséquence architecturale** : `design_gate.py` **ne doit PAS se contenter de lire l'exit code**. Il doit :
1. lancer `lint --format json`,
2. **parser le JSON** (`findings[].severity` / `path` / `message` + `summary`),
3. appliquer une **politique de sévérité propre à la forge** : ex. *« échec si tout finding `contrast-ratio` < AA, `broken-ref`, ou `missing-*` »* — quelle que soit la sévérité native.

Cela reste un adapter mince, mais **avec une couche de politique** (≠ simple wrapper d'exit code). C'est l'équivalent design du « ne pas réimplémenter, mais contraindre ».

### S-2.4 — Format JSON (exemple réel)
```json
{
  "findings": [
    { "severity": "warning", "path": "components.button-primary",
      "message": "textColor (#ffffff) on backgroundColor has contrast ratio 15.42:1 — passes WCAG AA." }
  ],
  "summary": { "errors": 0, "warnings": 1, "info": 1 }
}
```

### S-2.5 — Licence & vendoring
Apache 2.0 (usage commercial OK, attribution + mention des modifs). **Non forkable de fait** (propriété Google + CLA pour contribuer) mais **adoptable** → cohérent avec la décision 06 : *adopter tel quel, épingler `@0.3.0`*, ne pas forker. Pas de vendoring de code source ; on épingle la version npm dans `design.md.lock`.

---

## S-3 — Template & Toolkit SaaS : greffable par `copier` ?

### Réponse
**Oui, sans réserve.** `full-stack-fastapi-template` est **conçu pour être généré, pas importé** : *« Consommation : template de génération (Copier), pas une dépendance »*, *« prête à forker, ça marche tel quel »*. H3 **confirmée**.

### S-3.1 — Génération
- `copier copy` → puis renseignement du `.env`.
- Stack : FastAPI + SQLModel + Pydantic v2 / **React 19 + Vite 7 + Tailwind 4** / PostgreSQL + Alembic + JWT (argon2/bcrypt), client TS auto-généré (openapi-ts), Sentry.
- **14 workflows GitHub Actions** (= harness du gate code), 17 tests pytest + 12 Playwright, Docker Compose dev/prod + Traefik + HTTPS. Licence **MIT** (~43k★).

### S-3.2 — Les 11 briques SaaS (résout [`analyse.md`](analyse.md) §8.5)
> Statut sur le template + décision build/buy par défaut + action de scaffolding (back via `uv`).

| # | Brique | Statut | Décision | Action de scaffolding |
|---|---|---|---|---|
| 1 | **Auth** (OAuth/SSO/MFA) | Partiel (JWT natif) | Build Authlib / Buy WorkOS (SSO) | `cd backend && uv add authlib` |
| 2 | **RBAC** | Partiel (superuser/user) | **Build Casbin** | `cd backend && uv add casbin` |
| 3 | **Multi-tenancy** | À ajouter | **Build `tenant_id` row-level** | Table `Organization` + FK `organization_id` + dépendance d'isolation ; `alembic revision --autogenerate -m "add tenancy"` |
| 4 | **Billing** | À ajouter | **Buy Stripe** (Polar.sh/Lemon Squeezy si TVA UE) | `uv add stripe` + `POST /webhooks/stripe` (vérif signature) |
| 5 | **Observabilité** | Partiel (Sentry) | Build OpenTelemetry / Buy Grafana | OTel SDK |
| 6 | **Analytics produit** | À ajouter | Buy/self-host **PostHog** | intégration PostHog |
| 7 | **Feature flags** | À ajouter | **OpenFeature** SDK + Unleash (self-host) | SDK OpenFeature |
| 8 | **CRUD / API** | ✅ Couvert | Build (cœur métier) | natif (FastAPI + SQLModel) |
| 9 | **Emailing** | Partiel (SMTP+MJML) | **Buy Resend** + react-email | `npm i react-email @react-email/components` |
| 10 | **Jobs async** | À ajouter | **Build ARQ + Redis** (Buy Inngest si orchestration) | `uv add arq` + Redis |
| 11 | **Stats / dashboards** | À ajouter | Build Recharts + endpoints d'agrégation / Buy Metabase | Recharts (front) |

### S-3.3 — Multi-tenancy : décision tranchée (résout [`analyse.md`](analyse.md) §8.7)
Le Toolkit tranche **`tenant_id` row-level** (table `Organization`, FK `organization_id` sur les modèles, filtrage systématique par dépendance d'injection) — **PAS** RLS PostgreSQL ni schéma-par-tenant. Décision **structurante à prendre en t0** (décision canonique 05). C'est donc le modèle à implémenter dans `targets/fastapi-saas/bricks/multi-tenancy/`.

### S-3.4 — Vigilance
*« Le template évolue : revérifier sa composition avant tout réemploi. »* + *« Les choix build/buy sont des positions par défaut Digit-AI, à arbitrer selon le contexte client (volumétrie, conformité, budget, résidence des données). »* → les 3 briques de t0 (auth/SSO, RBAC, multi-tenancy) sont fixes ; les 8 autres restent paramétrables (décision 05/08).

---

## Impacts consolidés sur le projet

1. **`design_gate.py` = adapter + politique JSON** (pas un lecteur d'exit code). Correction propagée dans [`architecture.md`](architecture.md).
2. **Epic 1** peut citer les **commandes de scaffolding exactes** des briques (résout §8.5).
3. **Multi-tenancy = `tenant_id` row-level** (résout §8.7).
4. **Epic 2** : commande de lint figée + politique de gating à coder.
5. Aucun risque de conception résiduel sur S-2/S-3 ; reste de l'assemblage.

> Tous les dérisquages (S-1, S-1b, S-2, S-3) sont **résolus** → l'Epic 1 peut démarrer.
