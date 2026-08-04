---
name: digitai-minimal
summary: Style sobre et accessible Digit-AI — surfaces claires, accent bleu/violet, AA par défaut.
wcag: "2.2 AA"
---

# Style — digitai-minimal

Contexte design **injecté aux agents au dev de story** (décision 04). Vendorisé par **copie
locale** (DE-2) : aucune CLE `typeui.sh` à l'exécution. Source : `awesome-design-skills`
(style adapté), figé ici par copie.

## Tokens de référence

- Couleurs : `primary #2563eb`, `accent #5b21b6`, `ink #0f172a` sur `surface #ffffff`.
- Typo : titres **Roboto**, corps **DM Sans**, mono **JetBrains Mono**.
- Espacement : échelle 4 / 8 / 16 / 24 / 40 px.
- Rayons : `sm` 6, `card` 12, `pill` 999.

## Do

- Contraste texte/fond conforme **WCAG 2.2 AA** (vérifié par le gate design).
- Hiérarchie typographique nette ; un seul accent par écran.
- Composants dérivés des tokens (jamais de valeurs en dur).

## Don't

- Pas de dégradés criards ni d'ombres lourdes.
- Pas de couleur hors palette ; pas de taille de police arbitraire.
- Pas de densité excessive : laisser respirer (échelle d'espacement).

> Cet artefact est lu en local par `supervisor.py` (étape E) au moment du dev de chaque story.
