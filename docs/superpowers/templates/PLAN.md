<!-- TEMPLATE — copier en PLAN.md à la racine du run, remplacer <…>. Source de vérité + checkpoint de reprise. -->
# Run <slug> — Plan maître
> budget: <temps/coût max> · max_parallel: <n> · politique merge: <A|B|C> · branche: run/<slug>
> Statuts possibles : `todo` · `in-progress` · `done` · `blocked: <raison>`

| # | EPIC | dépend de | statut | gate | tests | durée | tag |
|---|------|-----------|--------|------|-------|-------|-----|
| 1 | <titre EPIC 1> | — | todo | — | — | — | — |
| 2 | <titre EPIC 2> | 1 | todo | — | — | — | — |
| 3 | <titre EPIC 3> | — | todo | — | — | — | — |

## Règles de mise à jour (l'orchestrateur les applique)
- Après chaque EPIC : mettre à jour `statut`, `gate` (✅/❌), `tests` (nb), `durée`, `tag`.
- `tag` = `run/<slug>/epic-<n>` posé UNIQUEMENT si double gate + non-régression verts.
- Une EPIC `blocked: <raison>` n'est ni mergée ni taguée ; elle est surfacée à la revue finale.
- Reprise : redémarrer à la 1ʳᵉ EPIC non `done` ; ne pas retaguer le `done`.
- Ce fichier est tenu à jour de façon ASYNCHRONE (jamais de message bloquant pour informer).
