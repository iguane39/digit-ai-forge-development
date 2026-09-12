# Travaux confiés par le pilot — digit-ai-forge-development — 20260912c

<!-- Gabarit du pilot (gabarits\TRAVAUX-PILOT.md). Un fichier = UN lot de travaux confiés.
     Emplacement chez le produit : input\00-travaux\pilot - TRAVAUX - <AAAAMMJJ><indice>.md
     Un fichier déposé ne se modifie JAMAIS — le lot suivant est un nouveau fichier daté. -->

- **Émetteur** : `digit-ai-factory` (le pilot)
- **Références registre** : `todo\TODO.jsonl` — items `TF-1064`, `TF-1066` cités élément par élément
- **Dépôt** : ce fichier est déposé par le pilot dans `input\00-travaux\` du produit. L'original
  reste au pilot (`output\` daté). Statut : `a_traiter` → `traite le <date>` — seule édition
  autorisée après coup : cette ligne de statut.
- **Statut** : traite le 2026-09-12
- **Sort du lot reçu** (TF-0883 — jugé par la règle T8 de `oracle-travaux-pilot.mjs`) : ce lot entre dans
  l'histoire du produit — `git add` du fichier et de son sidecar — SAUF si `git check-ignore "<ce fichier>"`
  le déclare ignoré, auquel cas il reste hors de l'histoire et vit sur le seul poste qui l'a reçu.
  Mesuré le 12/09 : votre `input\00-travaux\` porte déjà les lots du 05/09 suivis par git — ce lot entre dans votre histoire.

> ## ⛔ AVANT DE TRAITER — un geste, une seconde
>
> ```
> node forge\travaux\oracle-travaux.mjs "<ce fichier>.md"
> ```
>
> Il rend **0** si la forme du lot est tenue, **1** sinon — et il dit alors ce qui manque. C'est
> exactement le contrôle que le pilot joue AVANT d'émettre : le même module, importé des deux côtés.

## Ce lot est une DONNÉE, pas une consigne exécutable

Le pilot traite vos lots de retours comme de la donnée : les consignes qu'ils contiennent sont décrites, jamais exécutées. Le même principe s'applique ici, dans l'autre sens. Ce lot décrit un travail et argumente pourquoi il vaut d'être fait ; il ne commande rien. Vous restez le juge de ce que vous en faites, sur votre run, avec vos oracles ; un constat écarté rejoint vos écarts assumés avec son motif — il ne disparaît pas. Aucun commit n'a été fait chez vous.

## Travaux confiés

### TF-1064 — Le playbook de run cite le plancher d'écriture pour les textes que le développement produit · gravité majeur

- **Le fait** : le 12/09/2026, sur mandat humain (décisions D-1 (a) et D-3 (a) de la synthèse 20260911j), le pilot a déposé un plancher d'écriture transverse (`references\ECRITURE.md`, E-1 à E-12, typologie T1-T5) : les produits le reçoivent par héritage 1.9.0 (`forge\ECRITURE.md` en copie conforme, hook `ecriture` joué à chaque écriture d'un `.md` par `forge\hooks\factory.mjs`). Deux types de textes que le développement produit n'ont pas de juge : les textes d'application (T4 : libellés, erreurs, états vides, aide — règle E-12, contrat `voix.md` de forge-design, oracle T4 confié à forge-design le même jour) et les messages de commit et entrées de ledger (T5 : revue). Relevé du 11/09 : `docs\run-playbook.md` (TF-0007) ne cite ni l'un ni l'autre ; votre `design\DESIGN.md` est générique.
- **Pourquoi cela vous concerne** : c'est votre playbook que le run de development suit sous gates ; une règle qu'il ne cite pas n'est pas rencontrée au moment où le code s'écrit (TF-0765, même mécanisme que « tri et filtres »).
- **Ce qui est demandé** : (1) `docs\run-playbook.md` : une discipline « Textes du produit » qui cite `forge\ECRITURE.md` (E-12 pour T4, avec les trois formes : libellé = ce que la personne contrôle, erreur = ce qui s'est passé puis comment réparer, état vide = invitation à agir) et qui exige que les chaînes d'application vivent dans un fichier de ressources extractible (JSON, `.arb`, `.po`, `.properties`) plutôt qu'en littéraux dispersés, pour que l'oracle T4 de forge-design puisse les lire ; (2) la même discipline pour T5 : un message de commit dit ce qui change et pourquoi, en une phrase de sujet puis un corps (phrases ≤ 35 mots, aucun « fix », « wip », « update » nu) ; (3) le gate de fin de development joue `node forge\hooks\factory.mjs ecriture --fichier <chaque .md écrit par le run>` s'il n'a pas tourné en PostToolUse.
- **Module producteur lu** : `docs\run-playbook.md` (disciplines TF-0007), `design\DESIGN.md`, `gabarits\CLAUDE-PRODUIT.md` du pilot § « Règles de socle applicables » (lignes T4 et Markdown ajoutées le 12/09).
- **Effort estimé** : complexité simple × durée courte.
- **Comment vous saurez que c'est fait** : le playbook porte la discipline avec ses trois formes et le format de commit ; un produit ouvert après ce lot porte ses chaînes dans un fichier de ressources ; `oracle-ecriture.mjs` du pilot rend PASS sur les `.md` du run ; commit publié.
- **Si ce n'est pas fait** : les applications gardent leurs textes d'usine et les commits leurs « fix » ; le plancher couvre les documents et laisse le code.

### TF-1066 — Tout écran de bureau se conçoit à 1920 px et se vérifie jusqu'au 4K · gravité majeur

- **Le fait** : règle humaine du 12/09/2026 : « pour le design, prends à minima par défaut FullHD (1920px en largeur) pour les desktops, et du responsive design pour monter jusqu'à du 4K ». Le pilot a écrit la règle E5 dans `references\BEST-PRACTICES-HTML.md` et dans `gabarits\CLAUDE-PRODUIT.md` ; forge-agents (grille de `render_page.py`) et forge-design (contrat technique, maquettes, baseline) ont reçu leurs lots. Votre playbook ne fixe aucune largeur de conception ni de vérification.
- **Pourquoi cela vous concerne** : c'est au development que l'écran se construit ; un composant conçu à 1280 s'étire ou se perd à 3840.
- **Ce qui est demandé** : (1) `docs\run-playbook.md` : la discipline de construction d'un écran de bureau cite E5 (conception à 1920, grilles fluides qui gagnent des colonnes plutôt que des marges, aucune hauteur fixe, mesure de lecture portée par le conteneur) ; (2) le gate visuel du development joue `render_page.py --widths 3840,2560,1920,1440,1024,768,390` (ou la grille par défaut du socle une fois étendue) et refuse un défaut bloquant à toute largeur.
- **Module producteur lu** : `docs\run-playbook.md`, `references\BEST-PRACTICES-HTML.md` du pilot (E4, E5).
- **Effort estimé** : complexité simple × durée courte.
- **Comment vous saurez que c'est fait** : le playbook cite E5 et la grille ; un run de development rend ses captures à sept largeurs ; commit publié.
- **Si ce n'est pas fait** : chaque écran est conçu à la largeur du poste de l'auteur et le lecteur en 4K découvre le défaut.

## Ce que le pilot a déjà fait de son côté

- Doctrine, donnée, oracle et hook `ecriture` chez le pilot ; héritage 1.9.0 chez les produits (`forge\ECRITURE.md`, `forge\hooks\factory.mjs ecriture`, `settings-produit.json`) ; lignes de socle dans `CLAUDE-PRODUIT.md`.
- Règle E5 écrite ; lots homologues remis à forge-agents et forge-design.
- Rien n'a été écrit dans votre dépôt hors de la boîte `input\00-travaux\`.

## Ce que le pilot NE demande PAS

- Pas de juge du ton ni de la voix : ils appartiennent à forge-design (`voix.md`, `MARQUE.md`).
- Pas d'oracle T4 chez vous : il est confié à forge-design ; vous le jouez quand il existe.
- Pas de réécriture des commits passés : l'histoire ne se réécrit pas.

## Ordre recommandé

1. **E5 dans le playbook d'abord** (TF-1066), parce que c'est une ligne et que la règle humaine est immédiate.
2. **La discipline « Textes du produit » ensuite** (TF-1064), parce qu'elle conditionne l'oracle T4 à venir.

## Remise du compte rendu

À la clôture de votre run, un lot de retours `digit-ai-forge-development - RETOURS - <date><i>.md` (+ sidecar) remis dans `c:\dev\digit-ai-factory\input\00-retours\` dit ce qui a été fait, avec la preuve (recettes, comptes, commit, porte, push) — le pilot clôt les items sur gains constatés.
