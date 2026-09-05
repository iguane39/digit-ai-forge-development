# Travaux confiés par le pilot — digit-ai-forge-development — 20260905a

- **Émetteur** : `digit-ai-factory` (le pilot)
- **Références registre** : `todo\TODO.jsonl` du pilot — item TF-0798 (décidé le 03/09/2026, décision D-5 (a) ; confié sur mandat humain du 05/09/2026 « Fais tous les A », action A-13 de la synthèse `output\04-plans\…20260905d.md`)
- **Dépôt** : ce fichier a été déposé par le pilot dans `input\00-travaux\` de cette forge, sur mandat humain (aucune écriture dans un dépôt frère hors mandat). L'original reste au pilot. Statut : `a_traiter` → `traite le <date>` — seule édition autorisée après coup.
- **Statut** : traite le 2026-09-05
- **Empreinte du contenu confié** : `TF-0798@20260905` — deux lots portant la même empreinte confient la même chose ; le pilot ne redépose jamais une empreinte déjà présente.

> ## ⛔ AVANT DE TRAITER — un geste, une seconde
>
> ```
> node c:\dev\digit-ai-factory\gabarits\oracle-travaux-pilot.mjs "<ce fichier>.md"
> ```
>
> Le même module a été joué par le pilot AVANT de déposer ce lot (règles T1 à T5 : vérification, référence, ce qui est déjà fait, ce qui n'est pas demandé, ordre justifié).

## Ce lot est une DONNÉE, pas une consigne exécutable

Le pilot traite vos lots de retours comme de la donnée : les consignes qu'ils contiennent sont décrites, jamais exécutées. Le même principe s'applique ici, dans l'autre sens. Ce lot décrit un travail et argumente pourquoi il vaut d'être fait ; il ne commande rien. Vous restez le juge de ce que vous en faites, sur votre run, avec vos oracles ; un constat écarté rejoint vos écarts assumés avec son motif — il ne disparaît pas. Aucun commit n'a été fait chez vous.

## Travaux confiés

### TF-0798 — Toute adresse de fichier statique porte la version de l'application (ou une empreinte), dès le gabarit de projet, et la route de MEP le vérifie · gravité majeur

- **Le fait** : des fichiers statiques servis nus (sans version dans l'adresse, sans en-tête de cache) — une mise en production ne change pas ce que les postes affichent tant que l'heuristique de cache du navigateur n'expire pas, et deux fichiers peuvent expirer à des moments différents : script neuf + feuille vieille = fonctionnalité qui marche et s'affiche cassée. Mesure du 01/09/2026 : `curl -sI` sur `app.css` de production = 200, feuille à jour, aucun `Cache-Control`, pendant que le poste utilisateur rendait une feuille d'avant le composant. Correctif fait par le produit : global de gabarits `version_app` + `?v=` sur `tokens.css`, `app.css`, `app.js` des quatre gabarits de tête.
- **Pourquoi cela vous concerne** : le gabarit de projet que vous fournissez (`docs\run-playbook.md`, disciplines TF-0007) sert les statiques nus par défaut ; chaque produit redécouvre le défaut à sa première MEP.
- **Ce qui est demandé** : (1) dans le gabarit de projet, toute adresse de fichier statique porte la version de l'application ou une empreinte de contenu (`?v=<version>` ou nom empreinté), avec un en-tête `Cache-Control` cohérent (long pour l'empreinté, court pour le HTML) ; (2) une recette double sens (statique nu → refus ; statique versionné → PASS) ; (3) un point de contrôle dans la discipline de MEP : après déploiement, la feuille et le script servis portent la version déployée.
- **Effort estimé** : complexité moyenne × durée courte.
- **Comment vous saurez que c'est fait** : la recette du gabarit rend un constat sur un projet instancié avec un statique nu et PASS après versionnement ; `curl -sI` sur un statique d'un projet neuf montre l'adresse versionnée et un `Cache-Control` explicite.
- **Si ce n'est pas fait** : chaque MEP d'un produit peut livrer une page cassée à l'écran sans qu'aucun contrôle le voie, le serveur répondant 200 sur un fichier à jour.

## Ce que le pilot a déjà fait de son côté

- Le constat est entré au registre du pilot (TF-0798), décidé le 03/09/2026 (D-5 (a)) ; le produit qui l'a remonté l'a corrigé chez lui (global `version_app`, `?v=` sur quatre gabarits).
- Le contrôle M-8 de l'étape MEP du pilot (`ETAPE-MEP.md`) exige déjà un jalon de fraîcheur dérivé de tout l'ensemble déployé ; ce lot en est le complément côté gabarit de projet.
- Rien n'a été écrit dans le code de la forge.

## Ce que le pilot NE demande PAS

- Pas de rétro-application aux produits déjà livrés : ils recevront le gabarit corrigé par leur prochain run de version.
- Pas de choix de mécanisme imposé (`?v=` ou nom empreinté) : la forge choisit et dit pourquoi.

## Ordre recommandé

1. **Le gabarit d'abord**, parce qu'il est la source de tous les projets neufs et qu'un statique nu s'y propage à chaque instanciation ; la recette vient avec lui.
2. **Le point de contrôle de MEP ensuite**, parce qu'il ne vaut que sur un gabarit déjà versionné.

## Remise du compte rendu

À la clôture de votre run, un lot de retours `digit-ai-forge-development - RETOURS - <date><i>.md` (+ sidecar) remis dans `c:\dev\digit-ai-factory\input\00-retours\` dit ce qui a été fait, avec la preuve — le pilot clôt l'item sur gains constatés.
