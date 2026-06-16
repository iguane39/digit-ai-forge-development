# Digit-AI SaaS Forge

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · **Italiano** · [Português](README.pt.md)

> **Dall'idea a un SaaS pronto per la produzione, con un solo comando — sotto un doppio gate di codice e design.**

Digit-AI SaaS Forge è un acceleratore SaaS agentico. Uno **strato di orchestrazione sottile**
(`conductor/`) sequenzia e vincola motori di terze parti collaudati per portare un'intenzione
di prodotto fino a un repository SaaS strutturato, testato e conforme a una brand guide —
senza mai riscrivere né forkare tali motori.

La forge non reinventa né la pianificazione, né lo scaffolding, né lo sviluppo autonomo, né il
linting del design. Li **orchestra**.

## Come funziona — una catena in 5 fasi

| Fase | Nome | Ruolo |
|------|------|-------|
| **A** | Inquadramento | Trasformare un'idea + vincoli in una config di missione (target, ambito SaaS, brand) |
| **B** | Scaffold-first | Generare lo scheletro di produzione **prima di qualsiasi agente** |
| **C** | Ponte BMAD | Avviare la pianificazione agile → PRD, architettura, epic, story — *gate HITL 1* |
| **D** | Adattatore di sprint | Collocare il backlog dove il motore autonomo se lo aspetta |
| **E** | Supervisore | Eseguire lo sprint autonomo sotto il doppio gate — *gate HITL 2* |

Due principi strutturali:

- **Scaffold-first** — lo scheletro di produzione esiste prima che gli agenti scrivano una
  riga di codice.
- **Doppio gate** — nessuna story viene mergiata se non passano **entrambi**: la CI di codice
  (ruff, mypy, pytest, Playwright) **e** il lint di design (WCAG 2.2 AA, riferimenti rotti,
  on-system).

Due punti di validazione umana (HITL): approvazione di PRD e architettura, poi revisione e
merge finale. Il merge automatico è disabilitato per scelta progettuale.

## Motori orchestrati (fissati e vendorizzati, mai forkati)

| Motore | Strato |
|--------|--------|
| [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | Pianificazione agile (brief → PRD → story) |
| [bmad-autonomous-development](https://github.com/stephenleo/bmad-autonomous-development) | Esecuzione autonoma dello sprint (un worktree git per story) |
| [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | Target di produzione deterministico (FastAPI + React + PostgreSQL) |
| [@google/design.md](https://github.com/google-labs-code/design.md) | Lint del design system (il gate di design) |

## Struttura del repository

| Percorso | Contenuto |
|----------|-----------|
| [`digitai-saas-forge/`](digitai-saas-forge/) | Il codice: `conductor/` (framework master), target parametrizzabile, gate, CI |
| [`docs/`](docs/) | Corpus di progettazione: analisi, PRD (formato BMAD), architettura, piano di implementazione, note di spike, decisioni esecutive |
| [`input/`](input/) | Il dossier fondativo originale |

## Avvio rapido

```bash
cd digitai-saas-forge
uv sync
uv run pytest        # gate di codice (ruff + mypy strict + pytest)
conductor --version
```

## Stato

**Epic 0 (Bootstrap) — consegnato e verificato.** Scheletro `conductor/` tipizzato, contratti
della pipeline `A→E`, CI a doppio gate, vendoring di BAD `@v1.2.0`, seed di dogfooding. Il gate
di codice è verde su GitHub Actions. Prossimo: Epic 1 (scaffold-first), Epic 2 (asse design),
Epic 3 (ciclo completo) — vedi [`docs/plan-implementation.md`](docs/plan-implementation.md).

## Licenza

[MIT](LICENSE) © 2026 Digit-AI.

---
*Digit-AI · Consulenza e strategia IA · acceleratore SaaS · 2026*
