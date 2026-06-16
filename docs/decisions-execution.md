# Décisions d'exécution (post-spikes)

> Arbitrages humains tranchés le 16/06/2026, en clôture des spikes S-1→S-3.
> Distinctes des **décisions canoniques 01-08** du dossier fondateur (constitution du repo) : ce sont des décisions de **mise en œuvre**, qui lèvent les questions ouvertes du [`PRD.md`](PRD.md) §9.

| # | Décision | Statut |
|---|---|---|
| **DE-1** | Dogfooding BMAD **réel** | ✅ tranché |
| **DE-2** | Injection design = **copie locale** (pas de CLI) | ✅ tranché |
| **DE-3** | Gate : **3 retries** d'agent avant escalade HITL | ✅ tranché |
| **DE-4** | « PR-ready » = **checklist binaire de 6 items** | ✅ tranché |

---

## DE-1 — Dogfooding BMAD réel

**Décision** : la forge `digitai-saas-forge` est planifiée en **faisant réellement tourner BMAD-METHOD sur elle-même** — pas seulement « à la manière de ». Le repo possède donc son propre `_bmad-output/planning-artifacts/epics.md` et son `sprint-status.yaml`, générés par BMAD à partir d'un brief décrivant la forge.

**Conséquences**
- **Epic 0** doit installer BMAD (`npx bmad-method install --modules bmm,tea`) dans le repo de la forge lui-même.
- Le [`plan-implementation.md`](plan-implementation.md) (Epics 0→3 écrits à la main) sert de **brief d'amorçage** ; BMAD le re-formalise en artefacts versionnés.
- Bénéfice : la forge devient sa **propre première démonstration** (P1 construit avec les outils de P2). Coût : dépendance à BMAD dès l'Epic 0.

---

## DE-2 — Injection design par copie locale

**Décision** : les styles `awesome-design-skills` retenus sont **copiés une fois pour toutes dans `design/styles/`** (vendoring) et lus en local au dev de story. **La CLI `npx typeui.sh pull <slug>` n'est PAS utilisée** en exécution.

**Justification** : lève la contradiction interne du dossier (§8.4) en faveur de la mitigation du risque 6 (mono-auteur, sans release) et de la décision canonique 06 (vendoriser, copie sans CLI). Évite une dépendance réseau fragile à chaque dev de story.

**Conséquences**
- **Epic 2 / story 2.4** : copie locale (déjà prévue ainsi).
- `supervisor.py` (E) injecte le contexte design en **lisant `design/styles/<slug>/SKILL.md`**, sans appel CLI.
- La CLI `typeui.sh` peut rester un outil d'**amorçage manuel** (récupérer un style une fois), jamais une dépendance d'exécution.

---

## DE-3 — 3 retries de gate avant escalade HITL

**Décision** : sur échec du double gate d'une story, `supervisor.py` relance l'agent de story **jusqu'à 3 fois** (3 retries). Au 4ᵉ échec, la story est marquée bloquée et **escaladée en HITL** (pas de boucle infinie).

**Conséquences (FR-E5)**
- Paramètre exposé : `gate_max_retries = 3` (overridable par mission).
- Compteur par story ; après épuisement → statut `blocked` + notification (canal terminal/Telegram de BAD) + arrêt de cette story (les autres continuent).
- Borne le coût en tokens et l'acharnement d'un agent sur une story impossible.

---

## DE-4 — « PR-ready » = checklist binaire (6 items)

**Décision** : CS-1 est satisfait quand, **pour chaque story du sprint**, les 6 booléens suivants sont vrais :

1. 1 PR ouverte par story, **non mergée** (`auto_pr_merge=false`).
2. **Double gate vert** (jobs `code` + `design` de `double-gate.yml`).
3. **Corps de PR** non vide : résumé + critères d'acceptation cochés + lien vers la story dans `epics.md`.
4. **PR liée à son issue GitHub** (champ `**GH Issue:**`).
5. **`mergeable` = clean** (à jour avec la base, sans conflit).
6. **Assignée pour revue HITL 2** : reviewer humain + label `needs-human-review`.

**Conséquences**
- Items 1-5 vérifiables via `gh pr view --json state,mergeable,body,...` ; item 6 via assignation/labels.
- Devient le **test automatisé de CS-1** ([`PRD.md`](PRD.md) §7) et la **condition de sortie objective de l'Epic 3**.
- `supervisor.py` produit le corps de PR et l'assignation ; il ne merge jamais (HITL 2).
