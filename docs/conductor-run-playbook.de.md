# Conductor Run — Operator-Playbook

> 🌍 [English](conductor-run-playbook.md) · [Français](conductor-run-playbook.fr.md) · [Español](conductor-run-playbook.es.md) · [Deutsch](conductor-run-playbook.de.md) · [Italiano](conductor-run-playbook.it.md) · [Português](conductor-run-playbook.pt.md)

Dieses Playbook ist der Operator-Prompt, um einen End-to-End-`conductor run` der Digit-AI SaaS
Forge **aus einem anderen Claude-Code-Projekt** zu steuern, indem ein Spezifikations-/Constraints-
Dossier angehängt wird. Der Lauf ist orchestriert, aber **gesteuert**: Er hält per Design an zwei
menschlichen Kontrollpunkten (HITL) und mergt nie automatisch.

## Die Methodik auf einen Blick

```
Anhänge ─▶ [−1] klassifizieren (Umfang vs. Constraints)
       ─▶ [0]  Preflight (gh/Token, uv/node, Netzwerk, Forge klonen)
       ─▶ [A]  Scoping → MissionConfig (11 Bricks build/buy, t0 erzwungen)   ⟲ bestätigen
       ─▶ [B]  Scaffold-first (copier + Bricks, VOR jedem Agenten)
       ─▶ [C]  BMAD-Planung (epics.md)                                       ⛔ HITL 1
       ─▶ [D]  Sprint-Konfig (sprint-status.yaml + bad:, auto_pr_merge=false)
       ─▶ [E]  /bad-Sprint + Doppel-Gate (Code + Design) + 3 Retries          ⛔ HITL 2
                → PR-ready Pull Requests (nie automatisch gemergt)
```

Nicht verhandelbare Leitplanken: **Scaffold-first**, **Doppel-Gate** (Code-CI + Design-Lint),
**2 HITL**, **gepinnte/vendored Abhängigkeiten** (BAD `@v1.2.0`, `@google/design.md@0.3.0`),
**`auto_pr_merge=false`**.

## Der Operator-Prompt (in das andere Claude-Code-Projekt einfügen)

```markdown
# Mission — Einen `conductor run` (Digit-AI SaaS Forge) von der Idee bis PR-ready steuern

Du bist der Operator der `digit-ai-saas-forge` in DIESEM Projekt. Du führst einen Produktumfang
zu PR-ready Pull Requests, indem du die A→E-Kette des Conductors orchestrierst. Du darfst seine
Leitplanken NICHT umgehen.

## Eingaben (als ANHÄNGE bereitgestellt)
Eine oder mehrere Dateien sind angehängt (Specs, Constraints, technische Notizen — gemischte
Formate: md, pdf, docx, txt, Bilder). Sie sind NICHT vorsortiert.

Forge-Repo: https://github.com/iguane39/digit-ai-saas-forge
Ziel-PR-Repo (wo das SaaS generiert wird): {{ org/repo, oder "zu erstellen" }}

## Phase −1 — Anhänge analysieren & klassifizieren
Lies JEDEN Anhang vollständig, teile dann den Inhalt in zwei Kategorien — nichts erfinden,
nichts verlieren:
- **UMFANG (das "Was")**: Produktabsicht, Nutzer/Personas, Features, User Stories,
  Geschäftsregeln, Screens/Flows, Daten, Produkt-Erfolgskriterien.
- **CONSTRAINTS (das "Wie / in welchem Rahmen")**: vorgegebener Stack, Integrationen, Sicherheit/
  Compliance (DSGVO, Multi-Tenancy, RBAC, SSO…), Performance, Hosting, Budget, Frist, Marken-/
  Design-Charta, Test-/CI-Anforderungen, erlaubte Abhängigkeiten.
Regeln: eine mehrdeutige Anforderung → in beide einordnen und als "zu klären" markieren; weder
noch → als "außerhalb / ignorieren" auflisten; widersprechen sich Dateien → den Konflikt melden
(nicht allein entscheiden).
→ Erstelle eine KLASSIFIKATIONSTABELLE (Datei · Auszug · Kategorie · Notiz) und WARTE auf meine
Bestätigung der Sortierung vor dem Preflight. Sie ist die Grundlage von allem.

## Leitplanken (NICHT verhandelbar)
- **Scaffold-first**: das Produktionsgerüst existiert vor jedem Agenten (B vor C).
- **Doppel-Gate**: keine Story wird ausgeliefert, wenn Code-CI ODER Design-Lint fehlschlägt.
- **2 HITL**: (1) nach der BMAD-Planung, (2) vor jedem Merge. An JEDEM HITL HÄLTST du, legst
  eine Entscheidungszusammenfassung vor und WARTEST auf meine ausdrückliche Freigabe. Diese
  Stopps sind beabsichtigt — keine Fehler.
- **`auto_pr_merge=false`**: du mergest NIE automatisch. Du gibst dir kein HITL selbst frei.
- **Gepinnte/vendored Abhängigkeiten**: BAD `@v1.2.0`, `@google/design.md@0.3.0`.
- "End-to-End" = orchestriert ohne manuellen Schritt AUSSERHALB der 2 geplanten HITL.

## Phase 0 — Preflight (fail-fast: schlägt ein Punkt fehl, HALTE an und sage es)
1. `gh auth status` OK und `GITHUB_PERSONAL_ACCESS_TOKEN` exportiert (`export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)`).
2. `uv`, `node`/`npx`, `git`, Netzwerkzugang (npx/copier/bmad) verfügbar.
3. Forge erreichbar: klone sie und `uv sync` in `digitai-saas-forge/`.
4. Bestätige das Ziel-PR-Repo und den Zielordner des generierten SaaS.
→ Gib eine "Preflight OK/KO"-Tabelle aus, bevor du fortfährst.

## Phase A — Scoping (das Mapping = die eigentliche Arbeit)
Aus dem in Phase −1 bestätigten UMFANG + CONSTRAINTS, SCHLAGE eine explizite `MissionConfig` vor:
- `idea`: ein zusammenfassender Satz (NICHT die ganzen Anhänge).
- `target`: Ziel (Standard `fastapi-saas`).
- `saas_scope`: für JEDEN der 11 Bricks eine `build`/`buy`/`skip`-Entscheidung, BEGRÜNDET durch
  die Anhänge. Hinweis: `multi-tenancy`, `rbac`, `auth-sso` sind auf `build` ERZWUNGEN (t0).
- `brand_charter` + `style_slug`: ist keine Charta angehängt, sage es und schlage die Standard-
  `DESIGN.md` vor (das Design-Gate läuft darauf) — zu bestätigen.
- `budget`/`deadline` und `max_parallel_stories` (deckeln, Standard 2-3), um Kosten zu begrenzen.
- Liste Umfangsanforderungen auf, die du NICHT mappen konntest (Graubereich).
→ LEGE diese `MissionConfig` vor und WARTE auf meine Bestätigung vor Phase B (Scoping = Checkpoint).

## Phase B — Scaffold-first
Erzeuge das Gerüst via `copier` + pflanze die gewählten Bricks (t0 inklusive) ein. Prüfe, dass
das CI-Harness (Code-Gate) vorhanden ist. Rufe KEINEN Agenten vor Abschluss von B auf.

**Startkonfiguration (Onramp-Routing).** „Scaffold-first" verallgemeinert sich zu einem *Onramp*,
das `select_onramp` nach der Herkunft des Projekts wählt — alle erzeugen dasselbe Substrate, daher
sind die Phasen C→E für alle drei identisch:
- **From scratch** (`--mode greenfield`) → `ScaffoldOnramp`: erzeugt das Gerüst (dieser Abschnitt).
- **Fortsetzung** eines von der Forge erzeugten Projekts (`--mode brownfield`, Repo bereits konform)
  → `NoOnramp`: KEIN Scaffold; erfasst eine Baseline, die das Nicht-Regressions-Gate speist; plant
  nur die neuen Epics.
- **Externes** Projekt (`--mode brownfield`, zu normalisierendes Repo) → `AdapterOnramp`
  (unvollständiges FastAPI) oder `BuilderOnramp` (Nicht-FastAPI-Stack) + HITL-0 bei deklarierter
  Degradierung; dann `--intent remediation|complement|both`.

## Phase C — BMAD-Brücke → HITL 1
`npx bmad-method install --modules bmm,tea`, dann erzeuge die Planung in
`_bmad-output/planning-artifacts/epics.md` (PRD, Architektur, Epics, Stories).
→ **HITL 1**: lege eine Zusammenfassung PRD + Architektur + Epics/Stories vor. HALTE an. Schreibe
die Sprint-Konfig erst nach meinem "go".

## Phase D — Sprint-Adapter
Schreibe `_bmad-output/implementation-artifacts/sprint-status.yaml` und die `bad:`-Sektion von
`_bmad/config.yaml` mit **`auto_pr_merge: false`**, gedeckeltem `max_parallel_stories`,
Modell-Tiers. Kompiliere KEINEN Graphen (BAD baut ihn selbst).

## Phase E — Supervisor (Sprint unter dem Doppel-Gate)
Rufe den `/bad`-Skill auf (1 Worktree/Story, 7-Schritt-Pipeline, internes Code-Gate) mit
`AUTO_PR_MERGE=false`. Für jede Story:
- Design-Gate: `npx --yes -p @google/design.md@0.3.0 designmd lint --format json` DANN wende die
  Schweregrad-Policy an (vertraue NICHT dem Exit-Code: ein WCAG-Fehler kann als `warning`
  erscheinen → Exit 0). Blockiere bei Kontrast/Refs/fehlenden Sektionen sogar bei `warning`.
- Bei Gate-Fehler: bis zu **3 Retries** des Agenten, sonst Story als `blocked` markieren +
  eskalieren.
→ **HITL 2**: lege die PR-ready PRs vor (Checkliste: PR offen & nicht gemergt, Doppel-Gate grün,
generierter Body, verlinktes Issue, mergeable=clean, zur Prüfung zugewiesen) und alle `blocked`
Stories. HALTE an. MERGE NICHTS.

## Erwartete Ausgabe & Protokoll
- Ein LAUFPROTOKOLL: Anhang-Klassifikation, Status pro Phase, Scoping-Entscheidungen, ready vs
  blocked Stories, PR-Links, ungefähre Kosten/Zeit, Graubereiche.
- Erinnere daran, wo das generierte SaaS liegt und wie man nach jedem HITL FORTSETZT.
- Bei großem Umfang: schlage zuerst einen MVP-Slice / erstes Epic vor, lass ihn bestätigen, dann
  erweitere — statt den ganzen Sprint auf einmal zu starten.

## Verboten (schließe die Türen)
- Verarbeite Anhänge nicht, ohne sie gelesen & klassifiziert zu haben (Phase −1). Füge kein
  ganzes Dokument als `idea` ein. Überspringe den Preflight nicht. Erzwinge nicht
  `auto_pr_merge=true`. Gib dir kein HITL selbst frei. Ignoriere keinen Constraint, ohne ihn im
  Graubereich zu markieren. Forke nicht BMAD/BAD/das Template/design.md.
```

## Reale Ingestion (Pilot)

Die Ingestion ist standardmäßig heuristisch (deterministisch, kein Netzwerk). Um den **echten
Sub-Agenten-Analyzer** (`claude -p`) zu aktivieren, setze `CONDUCTOR_USE_CLAUDE_ANALYZER=1`
(erfordert das authentifizierte `claude`-CLI). Der bedingte Integrationstest dokumentiert den
Pfad: `RUN_CLAUDE_INTEGRATION=1 uv run pytest tests/test_claude_integration.py`.

## Realer autonomer Sprint (`/bad`, Pilot)

Der autonome BAD-Sprint ist **standardmäßig deaktiviert**. Um ihn zu aktivieren, setze
`CONDUCTOR_ENABLE_REAL_BAD=1` (erfordert authentifiziertes `claude` und `gh`).
Sicherheitshaltung: Der Lauf stützt sich auf BADs native Isolation (ein Git-Worktree pro
Story), `AUTO_PR_MERGE=false` ist typgesperrt (mergt nie automatisch), und HITL 2 steuert
weiterhin jeden Merge. `/bad` läuft mit `--dangerously-skip-permissions` und entspannter
Netzwerkisolation — **führe es nur auf einem Repo aus, dessen `main`-Branch geschützt ist;
niemals auf sensiblem Client-Code ohne Review.** Ergebnisse werden über `gh pr list`
(die Quelle der Wahrheit) beobachtet und auf Story-Ergebnisse gemappt.

## Reale BMAD-Planung (Pilot)

Die BMAD-Planung wird standardmäßig erfasst (`DefaultBmadPlanner` installiert BMAD und liest
die Artefakte; HITL 1 pausiert, wenn nicht vorhanden). Um die **autonome BMAD-Planung** über
`claude -p` zu aktivieren, setze `CONDUCTOR_ENABLE_REAL_BMAD=1` (erfordert authentifiziertes
`claude`). Sie erzeugt nur Planungsdokumente unter `_bmad-output/planning-artifacts/` und wird
immer durch **HITL 1** vor jeder Entwicklung gesteuert — kein Code wird geändert und nichts
wird in dieser Phase gemergt. Mit allen drei Opt-ins aktiviert
(`CONDUCTOR_USE_CLAUDE_ANALYZER`, `CONDUCTOR_ENABLE_REAL_BMAD`, `CONDUCTOR_ENABLE_REAL_BAD`),
läuft die vollständige `A→E`-Kette echt durch und hält trotzdem an beiden HITL-Gates an.
