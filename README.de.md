# Digit-AI SaaS Forge

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · **Deutsch** · [Italiano](README.it.md) · [Português](README.pt.md)

> **Von der Idee zu einem produktionsreifen SaaS, in einem Befehl — unter einem doppelten Code- & Design-Gate.**

Digit-AI SaaS Forge ist ein agentischer SaaS-Beschleuniger. Eine **schlanke
Orchestrierungsschicht** (`conductor/`) sequenziert und beschränkt bewährte Drittanbieter-
Engines, um eine Produktidee bis zu einem strukturierten, getesteten und markenkonformen
SaaS-Repository zu führen — ohne diese Engines jemals umzuschreiben oder zu forken.

Die Forge erfindet weder Planung, Scaffolding, autonome Entwicklung noch Design-Linting neu.
Sie **dirigiert** sie.

## Funktionsweise — eine Kette aus 5 Phasen

| Phase | Name | Aufgabe |
|-------|------|---------|
| **A** | Scoping | Idee + Rahmenbedingungen in eine Mission-Config überführen (Ziel, SaaS-Umfang, Marke) |
| **B** | Scaffold-first | Das Produktionsgerüst **vor jedem Agenten** erzeugen |
| **C** | BMAD-Brücke | Agile Planung starten → PRD, Architektur, Epics, Stories — *Gate HITL 1* |
| **D** | Sprint-Adapter | Das Backlog dorthin platzieren, wo die autonome Engine es erwartet |
| **E** | Supervisor | Den autonomen Sprint unter dem doppelten Gate ausführen — *Gate HITL 2* |

Zwei strukturelle Prinzipien:

- **Scaffold-first** — das Produktionsgerüst existiert, bevor Agenten eine Zeile Code
  schreiben.
- **Doppeltes Gate** — keine Story wird gemergt, wenn nicht **beide** bestehen: die Code-CI
  (ruff, mypy, pytest, Playwright) **und** das Design-Lint (WCAG 2.2 AA, defekte Referenzen,
  on-system).

Zwei menschliche Kontrollpunkte (HITL): Freigabe von PRD & Architektur, dann finale Prüfung &
Merge. Automatisches Mergen ist bewusst deaktiviert.

## Orchestrierte Engines (gepinnt & vendored, niemals geforkt)

| Engine | Schicht |
|--------|---------|
| [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | Agile Planung (Brief → PRD → Stories) |
| [bmad-autonomous-development](https://github.com/stephenleo/bmad-autonomous-development) | Autonome Sprint-Ausführung (ein Git-Worktree pro Story) |
| [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | Deterministisches Produktionsziel (FastAPI + React + PostgreSQL) |
| [@google/design.md](https://github.com/google-labs-code/design.md) | Design-System-Lint (das Design-Gate) |

## Repository-Struktur

| Pfad | Inhalt |
|------|--------|
| [`digitai-saas-forge/`](digitai-saas-forge/) | Der Code: `conductor/` (Master-Framework), parametrisierbares Ziel, Gates, CI |
| [`docs/`](docs/) | Design-Korpus: Analyse, PRD (BMAD-Format), Architektur, Implementierungsplan, Spike-Notizen, Ausführungsentscheidungen |
| [`input/`](input/) | Das ursprüngliche Gründungsdossier |

## Schnellstart

```bash
cd digitai-saas-forge
uv sync
uv run pytest        # Code-Gate (ruff + strenges mypy + pytest)
conductor --version
```

## Status

- **Epic 0 — Bootstrap** ✅ gemergt. Typisiertes `conductor/`-Gerüst, `A→E`-Verträge, Double-Gate-CI, BAD-Vendoring `@v1.2.0`, Dogfooding-Seed.
- **Epic 1 — Scaffold-first** ✅ gemergt. Scoping (A) + Scaffold (B) + 11-Bricks-Katalog + Code-Gate.
- **Epic 2 — Design-Achse** ✅ gemergt. Blockierendes Design-Gate (`@google/design.md@0.3.0` + Schweregrad-Policy), `DESIGN.md`, vendorter Style, Token-Export.
- **Epic 3 — Vollständige Schleife** ✅ gemergt. BMAD-Brücke (C) + HITL 1, Sprint-Adapter (D), Supervisor (E) ruft `/bad` auf mit Design-Gate pro Story, 3-Retry-Remediation und HITL 2 — automatisches Mergen gesperrt.

Alle vier Epics sind integriert; beide Gates sind grün auf GitHub Actions. Die `A→E`-Kette ist verdrahtet und getestet; die reale Ausführung von BMAD/`/bad` erfordert einen Claude-Code-Harness. Siehe [`docs/plan-implementation.md`](docs/plan-implementation.md).

## Einen Build starten — Methodik

Der Lauf ist orchestriert, aber **gesteuert**: Er hält per Design an zwei menschlichen
Kontrollpunkten und mergt nie automatisch. Man hängt ein Specs-/Constraints-Dossier an; der
Operator trennt Umfang von Constraints und durchläuft dann die Kette:

1. **Klassifizieren** der Anhänge — Umfang (das *Was*) vs. Constraints (das *Wie*).
2. **Preflight** — `gh` Auth + Token, `uv`/`node`, Netzwerk, Forge klonen.
3. **Scoping (A)** — `MissionConfig` ableiten (11 Bricks build/buy, t0 erzwungen), dann bestätigen.
4. **Scaffold-first (B)** — das Gerüst vor jedem Agenten erzeugen.
5. **BMAD-Planung (C) → HITL 1** — PRD/Architektur/Epics; menschliche Freigabe erforderlich.
6. **Sprint-Konfig (D)** — Backlog-Layout + `bad:`-Sektion (`auto_pr_merge=false`).
7. **Überwachter Sprint (E) → HITL 2** — `/bad` pro Story, Doppel-Gate, 3 Retries; kein Merge ohne menschliche Prüfung.

Vollständiger Operator-Prompt: **[`docs/conductor-run-playbook.md`](docs/conductor-run-playbook.md)**.

## Lizenz

[MIT](LICENSE) © 2026 Digit-AI.

---
*Digit-AI · KI-Beratung & -Strategie · SaaS-Beschleuniger · 2026*
