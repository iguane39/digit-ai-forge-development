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

**Epic 0 (Bootstrap) — geliefert & verifiziert.** Typisiertes `conductor/`-Gerüst,
`A→E`-Pipeline-Verträge, Double-Gate-CI, BAD-Vendoring `@v1.2.0`, Dogfooding-Seed. Das
Code-Gate ist grün auf GitHub Actions. Als Nächstes: Epic 1 (Scaffold-first), Epic 2
(Design-Achse), Epic 3 (vollständige Schleife) — siehe [`docs/plan-implementation.md`](docs/plan-implementation.md).

## Lizenz

[MIT](LICENSE) © 2026 Digit-AI.

---
*Digit-AI · KI-Beratung & -Strategie · SaaS-Beschleuniger · 2026*
