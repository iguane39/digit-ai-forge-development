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

> 📊 **Panoramica:** [diagramma interattivo del processo — 6 lingue](https://iguane39.github.io/digit-ai-saas-forge/forge-process-schema.html?lang=it) (ingressi · A→E · gate · HITL · ciclo iterativo).

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

- **Epic 0 — Bootstrap** ✅ integrato. Scheletro `conductor/` tipizzato, contratti `A→E`, CI a doppio gate, vendoring di BAD `@v1.2.0`, seed di dogfooding.
- **Epic 1 — Scaffold-first** ✅ integrato. Inquadramento (A) + scaffold (B) + catalogo 11 brick + gate di codice.
- **Epic 2 — Asse design** ✅ integrato. Gate di design bloccante (`@google/design.md@0.3.0` + politica di severità), `DESIGN.md`, stile vendorizzato, export di token.
- **Epic 3 — Ciclo completo** ✅ integrato. Ponte BMAD (C) + HITL 1, adattatore di sprint (D), supervisore (E) che invoca `/bad` con gate di design per story, remediation a 3 retry e HITL 2 — merge automatico bloccato.

I quattro epic sono integrati; entrambi i gate sono verdi su GitHub Actions. La catena `A→E` è cablata e testata; l'esecuzione reale di BMAD/`/bad` richiede un harness Claude Code. Vedi [`docs/plan-implementation.md`](docs/plan-implementation.md).

## Avviare un build — metodologia

L'esecuzione è orchestrata ma **governata**: si ferma a due checkpoint umani per progettazione
e non fa mai merge automatico. Si allega un dossier specifiche/vincoli; l'operatore separa il
perimetro dai vincoli, poi percorre la catena:

1. **Classificare** gli allegati — perimetro (il *cosa*) vs vincoli (il *come*).
2. **Preflight** — `gh` auth + token, `uv`/`node`, rete, clone della forge.
3. **Inquadramento (A)** — derivare un `MissionConfig` (11 brick build/buy, t0 forzate), poi validare.
4. **Scaffold-first (B)** — generare lo scheletro prima di qualsiasi agente.
5. **Pianificazione BMAD (C) → HITL 1** — PRD/architettura/epic; approvazione umana richiesta.
6. **Config di sprint (D)** — layout del backlog + sezione `bad:` (`auto_pr_merge=false`).
7. **Sprint supervisionato (E) → HITL 2** — `/bad` per story, doppio gate, 3 retry; nessun merge senza revisione umana.

**Inizia qui — punto di ingresso unico:** **[`docs/run-playbook.md`](docs/run-playbook.md)**. Aggiorna la forge, rileva il tuo contesto (nuovo / continuazione / repo esterno / aggiornamento della forge) e instrada al flusso giusto. Riferimenti di dettaglio: [`conductor-run-playbook.it.md`](docs/conductor-run-playbook.it.md) (fasi A→E) e [`unattended-run-playbook.md`](docs/superpowers/unattended-run-playbook.md) (modalità autonoma «lancia e torna»).

## Licenza

[MIT](LICENSE) © 2026 Digit-AI.

---
*Digit-AI · Consulenza e strategia IA · acceleratore SaaS · 2026*
