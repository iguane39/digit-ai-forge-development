# Conductor Run — Playbook dell'operatore

> 🌍 [English](conductor-run-playbook.md) · [Français](conductor-run-playbook.fr.md) · [Español](conductor-run-playbook.es.md) · [Deutsch](conductor-run-playbook.de.md) · [Italiano](conductor-run-playbook.it.md) · [Português](conductor-run-playbook.pt.md)

Questo playbook è il prompt dell'operatore per guidare un `conductor run` end-to-end della
Digit-AI SaaS Forge **da un altro progetto Claude Code**, allegando un dossier di
specifiche/vincoli. L'esecuzione è orchestrata ma **governata**: si ferma a due checkpoint umani
(HITL) per progettazione e non fa mai merge automatico.

## La metodologia in una schermata

```
allegati ─▶ [−1] classificare (perimetro vs vincoli)
        ─▶ [0]  preflight (gh/token, uv/node, rete, clone forge)
        ─▶ [A]  inquadramento → MissionConfig (11 brick build/buy, t0 forzate)  ⟲ validare
        ─▶ [B]  scaffold-first (copier + brick, PRIMA di qualsiasi agente)
        ─▶ [C]  pianificazione BMAD (epics.md)                                  ⛔ HITL 1
        ─▶ [D]  config di sprint (sprint-status.yaml + bad:, auto_pr_merge=false)
        ─▶ [E]  sprint /bad + doppio gate (codice + design) + 3 retry            ⛔ HITL 2
                → Pull Request PR-ready (mai mergiate automaticamente)
```

Garanzie non negoziabili: **scaffold-first**, **doppio gate** (CI codice + lint design),
**2 HITL**, **dipendenze fissate/vendorizzate** (BAD `@v1.2.0`, `@google/design.md@0.3.0`),
**`auto_pr_merge=false`**.

## Il prompt dell'operatore (incolla nell'altro progetto Claude Code)

```markdown
# Missione — Guidare un `conductor run` (Digit-AI SaaS Forge) dall'idea al PR-ready

Sei l'operatore della `digit-ai-saas-forge` in QUESTO progetto. Porterai un perimetro di
prodotto fino a Pull Request PR-ready, orchestrando la catena A→E del conductor. NON sei
autorizzato a bypassare le sue garanzie.

## Input (forniti come ALLEGATI)
Uno o più file sono allegati (specifiche, vincoli, note tecniche — formati vari: md, pdf, docx,
txt, immagini). NON sono pre-ordinati.

Repo della forge: https://github.com/iguane39/digit-ai-saas-forge
Repo destinazione delle PR (dove si genera il SaaS): {{ org/repo, o "da creare" }}

## Fase −1 — Analizzare e classificare gli allegati
Leggi OGNI allegato per intero, poi separa il contenuto in due categorie — senza inventare nulla,
senza perdere nulla:
- **PERIMETRO (il "cosa")**: intento di prodotto, utenti/personas, funzionalità, user story,
  regole di business, schermate/flussi, dati, criteri di successo di prodotto.
- **VINCOLI (il "come / in quale quadro")**: stack imposto, integrazioni, sicurezza/conformità
  (GDPR, multi-tenancy, RBAC, SSO…), performance, hosting, budget, scadenza, brand/design,
  requisiti di test/CI, dipendenze consentite.
Regole: un requisito ambiguo → mettilo in entrambe e segnalalo "da arbitrare"; qualcosa che non è
nessuna delle due → elencalo come "fuori quadro / ignorare"; se i file si contraddicono → segnala
il conflitto (non decidere da solo).
→ Produci una TABELLA DI CLASSIFICAZIONE (File · Estratto · Categoria · Nota) e ATTENDI la mia
validazione dell'ordinamento prima del preflight. È la base di tutto il resto.

## Garanzie (NON negoziabili)
- **Scaffold-first**: lo scheletro di produzione esiste prima di qualsiasi agente (B prima di C).
- **Doppio gate**: nessuna story viene consegnata se la CI codice O il lint design fallisce.
- **2 HITL**: (1) dopo la pianificazione BMAD, (2) prima di qualsiasi merge. A OGNI HITL ti
  FERMI, presenti un riepilogo decisionale e ATTENDI la mia approvazione esplicita. Queste soste
  sono volute — non sono guasti.
- **`auto_pr_merge=false`**: non fai MAI auto-merge. Non ti auto-approvi alcun HITL.
- **Regola di merge**: l'integrazione per EPIC è **automatica e locale** (solo se il doppio gate è verde); l'unico merge **umano** è verso GitHub/`main`, **una volta, alla fine** (HITL 2). Una EPIC bloccata non viene mergiata.
- **Dipendenze fissate/vendorizzate**: BAD `@v1.2.0`, `@google/design.md@0.3.0`.
- "End-to-end" = orchestrato senza passo manuale FUORI dai 2 HITL previsti.

## Fase 0 — Preflight (fail-fast: se un punto fallisce, FERMATI e dillo)
1. `gh auth status` OK e `GITHUB_PERSONAL_ACCESS_TOKEN` esportato (`export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)`).
2. `uv`, `node`/`npx`, `git`, accesso di rete (npx/copier/bmad) disponibili.
3. Forge raggiungibile: clonala e `uv sync` in `digitai-saas-forge/`.
4. Conferma il repo destinazione delle PR e la cartella di destinazione del SaaS generato.
→ Restituisci una tabella "preflight OK/KO" prima di continuare.

## Fase A — Inquadramento (il mapping = il vero lavoro)
Dal PERIMETRO + VINCOLI validati in Fase −1, PROPONI un `MissionConfig` esplicito:
- `idea`: una frase di sintesi (NON gli allegati interi).
- `target`: target (default `fastapi-saas`).
- `saas_scope`: per CIASCUNO degli 11 brick, una decisione `build`/`buy`/`skip` GIUSTIFICATA
  dagli allegati. Nota: `multi-tenancy`, `rbac`, `auth-sso` sono FORZATE a `build` (t0).
- `brand_charter` + `style_slug`: se non è allegata alcuna charta, segnalalo e proponi il
  `DESIGN.md` di default (il lint design gira su di esso) — da validare.
- `budget`/`deadline` e `max_parallel_stories` (limitalo, default 2-3) per limitare i costi.
- Elenca i requisiti di perimetro che NON sei riuscito a mappare (zona grigia).
→ PRESENTA questo `MissionConfig` e ATTENDI la mia validazione prima della Fase B (inquadramento = checkpoint).

## Fase B — Scaffold-first
Genera lo scheletro via `copier` + innesta i brick scelti (t0 inclusi). Verifica che l'harness CI
(gate codice) sia in posizione. NON invocare alcun agente prima della fine di B.

**Configurazione di partenza (instradamento onramp).** Lo «scaffold-first» si generalizza in un
*onramp* scelto da `select_onramp` in base alla provenienza del progetto — tutti producono lo stesso
substrate, quindi le Fasi C→E sono identiche per le tre:
- **From scratch** (`--mode greenfield`) → `ScaffoldOnramp`: genera lo scheletro (questa sezione).
- **Continuazione** di un progetto generato dalla forge (`--mode brownfield`, repo già conforme) →
  `NoOnramp`: NESSUNO scaffold; cattura una baseline che alimenta il gate di non regressione;
  pianifica solo gli epic nuovi.
- **Progetto esterno** (`--mode brownfield`, repo da normalizzare) → `AdapterOnramp` (FastAPI
  incompleto) o `BuilderOnramp` (stack non-FastAPI) + HITL-0 se viene dichiarato un degrado; poi
  `--intent remediation|complement|both`.

## Fase C — Ponte BMAD → HITL 1
`npx bmad-method install --modules bmm,tea`, poi produci la pianificazione in
`_bmad-output/planning-artifacts/epics.md` (PRD, architettura, epic, story).
→ **HITL 1**: presenta un riepilogo PRD + architettura + epic/story. FERMATI. Scrivi la config di
sprint solo dopo il mio "go".

## Fase D — Adattatore di sprint
Scrivi `_bmad-output/implementation-artifacts/sprint-status.yaml` e la sezione `bad:` di
`_bmad/config.yaml` con **`auto_pr_merge: false`**, `max_parallel_stories` limitato, tier di
modelli. NON compilare un grafo (BAD lo costruisce da solo).

## Fase E — Supervisore (sprint sotto il doppio gate)
Invoca lo skill `/bad` (1 worktree/story, pipeline a 7 passi, gate codice interno) con
`AUTO_PR_MERGE=false`. Per ogni story:
- Gate design: `npx --yes -p @google/design.md@0.3.0 designmd lint --format json` POI applica la
  politica di severità (NON fidarti dell'exit code: un fallimento WCAG può uscire come `warning`
  → exit 0). Blocca su contrasto/refs/sezioni mancanti anche in `warning`.
- In caso di fallimento di un gate: fino a **3 retry** dell'agente, altrimenti segna la story
  `blocked` + escala.
→ **HITL 2**: presenta le PR PR-ready (checklist: PR aperta e non mergiata, doppio gate verde,
corpo generato, issue collegata, mergeable=clean, assegnata a revisione) e le story `blocked`.
FERMATI. NON MERGIARE NULLA.

## Output atteso e log
- Un LOG DI ESECUZIONE: classificazione degli allegati, stato per fase, decisioni di
  inquadramento, story ready vs blocked, link delle PR, costo/tempo approssimativi, zone grigie.
- Ricorda dove vive il SaaS generato e come RIPRENDERE dopo ogni HITL.
- Se il perimetro è grande: proponi prima uno slice MVP / primo epic, fallo validare, poi estendi
  — invece di lanciare tutto lo sprint in una volta.

## Vietato (chiudi le porte)
- Non elaborare gli allegati senza averli letti e classificati (Fase −1). Non incollare un
  documento intero come `idea`. Non saltare il preflight. Non forzare `auto_pr_merge=true`. Non
  auto-approvarti alcun HITL. Non ignorare alcun vincolo senza segnalarlo in zona grigia. Non
  forkare BMAD/BAD/il template/design.md.
```

## Ingestione reale (pilota)

L'ingestione è euristica per impostazione predefinita (deterministica, senza rete). Per
attivare il **sub-agente analizzatore reale** (`claude -p`), imposta
`CONDUCTOR_USE_CLAUDE_ANALYZER=1` (richiede il CLI `claude` autenticato). Il test di
integrazione condizionale documenta il percorso:
`RUN_CLAUDE_INTEGRATION=1 uv run pytest tests/test_claude_integration.py`.

## Sprint autonomo reale (`/bad`, pilota)

Lo sprint BAD autonomo è **disattivato per impostazione predefinita**. Per attivarlo, imposta
`CONDUCTOR_ENABLE_REAL_BAD=1` (richiede `claude` e `gh` autenticati). Postura di sicurezza:
l'esecuzione si affida all'isolamento nativo di BAD (un worktree git per story),
`AUTO_PR_MERGE=false` è bloccato per tipo (non fa mai auto-merge), e HITL 2 controlla ancora
ogni merge. `/bad` viene eseguito con `--dangerously-skip-permissions` e isolamento di rete
allentato — **eseguilo solo su un repo la cui branch `main` sia protetta; mai su codice
cliente sensibile senza revisione.** I risultati vengono osservati tramite `gh pr list`
(la fonte di verità) e mappati agli esiti per story.

## Pianificazione BMAD reale (pilota)

La pianificazione BMAD viene raccolta per impostazione predefinita (`DefaultBmadPlanner`
installa BMAD e legge gli artefatti; HITL 1 mette in pausa se assente). Per attivare la
**pianificazione BMAD autonoma** tramite `claude -p`, imposta `CONDUCTOR_ENABLE_REAL_BMAD=1`
(richiede `claude` autenticato). Produce solo documenti di pianificazione sotto
`_bmad-output/planning-artifacts/` ed è sempre controllata da **HITL 1** prima di qualsiasi
sviluppo — nessun codice viene modificato e nulla viene mergiato in questa fase. Con tutti e
tre gli opt-in attivi (`CONDUCTOR_USE_CLAUDE_ANALYZER`, `CONDUCTOR_ENABLE_REAL_BMAD`,
`CONDUCTOR_ENABLE_REAL_BAD`), la catena `A→E` completa viene eseguita sul serio, facendo
comunque pausa a entrambi i gate HITL.

## Gate di conformità allo spec reale (pilota)

Il gate di conformità allo spec è **disattivato per impostazione predefinita** (il supervisore
esegue solo il doppio gate + la non regressione). Per attivare una **revisione di conformità per
story** via `claude -p`, impostare `CONDUCTOR_ENABLE_SPEC_REVIEW=1` (richiede `claude` autenticato).
Confronta i criteri di accettazione di ogni story con il diff della sua PR: un **under-build**
(criterio non soddisfatto) blocca la story (entra nella remediation limitata a 3 retry, poi
`blocked`); un **over-build** (comportamento oltre lo spec) è consultivo. Tutti i findings sono
persistiti in `SPEC_FINDINGS.md` con uno stato `traité`/`non-traité` per la ripresa manuale
successiva. Nessun merge è interessato; HITL 2 è invariato.
