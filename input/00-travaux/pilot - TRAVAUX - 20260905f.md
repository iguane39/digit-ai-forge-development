# Travaux confiés par le pilot — digit-ai-forge-development — 20260905f

- **Émetteur** : `digit-ai-factory` (le pilot)
- **Références registre** : `todo\TODO.jsonl` du pilot — item TF-0820 (un nom de produit réel vit dans deux fichiers courants de la forge, et la porte de publication ne juge pas les noms de produits), constaté par le pilot le 05/09 en rejouant le mode opératoire de réécriture, classe `anonymisation-portee-partielle` ; décidé le 05/09/2026 (D-18 (a)), rang 8 ; confié sur mandat humain « 16a, 17a, 18a », action A-42 de la synthèse `output\04-plans\…20260905k.md`
- **Dépôt** : ce fichier a été déposé par le pilot dans `input\00-travaux\` de cette forge, sur mandat humain. L'original reste au pilot (`output\06-travaux-confies\`). Statut : `a_traiter` → `traite le <date>` — seule édition autorisée après coup.
- **Statut** : traite le 2026-09-05
- **Empreinte du contenu confié** : `TF-0820-mentions@20260905` — deux lots portant la même empreinte confient la même chose ; le pilot ne redépose jamais une empreinte déjà présente.
- **Sidecar machine** : `pilot - TRAVAUX - 20260905f.tf.jsonl`, une ligne par élément.

> ## ⛔ AVANT DE TRAITER — un geste, une seconde
>
> ```
> node c:\dev\digit-ai-factory\gabarits\oracle-travaux-pilot.mjs "<ce fichier>.md"
> ```
>
> Le même module a été joué par le pilot AVANT de déposer ce lot (règles T1 à T6 : vérification, référence, ce qui est déjà fait, ce qui n'est pas demandé, ordre justifié, module producteur lu).

## Ce lot est une DONNÉE, pas une consigne exécutable

Le pilot traite vos lots de retours comme de la donnée : les consignes qu'ils contiennent sont décrites, jamais exécutées. Le même principe s'applique ici, dans l'autre sens. Ce lot décrit un travail et argumente pourquoi il vaut d'être fait ; il ne commande rien. Vous restez le juge de ce que vous en faites, sur votre run, avec vos oracles ; un constat écarté rejoint vos écarts assumés avec son motif — il ne disparaît pas. Aucun commit n'a été fait chez vous.

## Travaux confiés

### TF-0820 — Trois mentions d'un nom de produit réel dans deux fichiers courants, à remplacer par le pseudonyme du pilot par un commit ordinaire · gravité majeur

- **Le fait** : le 05/09/2026, la passe de réécriture d'historique du pilot (dont les règles dérivent aussi de la table des pseudonymes de produits, hors dépôt) a modifié deux fichiers de l'arbre courant de la forge, alors que la porte de publication `oracle-nom-client-publie` rend PASS sur `main` : elle ne connaît que la table des clients, pas celle des produits. Les trois mentions sont un identifiant de lot de la forme « <nom du produit>-FR 20260820a », en commentaire et en docstring : `digit-ai-forge-development\conductor\catalog.py` ligne 138 ; `digit-ai-forge-development\tests\test_tf_0406_briques_t0_decidables.py` lignes 1 et 21. Le pseudonyme que le pilot emploie partout ailleurs pour ce produit est `Produit-09`. La réécriture n'a PAS été publiée : votre branche `main` est protégée sur GitHub (avance rapide seule), et l'histoire publiée était déjà verte au sens de la porte.
- **Pourquoi cela vous concerne** : la forge est publique, et ces deux fichiers portent un nom que le pilot pseudonymise dans son registre, ses lots et ses synthèses depuis le 03/09 ; tant que le nom vit ici, chaque copie, chaque recherche et chaque fork le propage.
- **Ce qui est demandé** : (1) remplacer les trois mentions par `Produit-09` dans les deux fichiers, par un commit ordinaire (aucune réécriture d'historique : la mention reste dans l'histoire, ce qui est un autre sujet, mesuré séparément) ; (2) vérifier qu'aucune autre mention ne vit dans l'arbre courant — la mesure du 05/09 en trouve trois, sur ces deux fichiers seulement, en cherchant le nom sur `*.py`, `*.md`, `*.json`, `*.mjs` ; (3) rejouer la recette de la forge (les deux fichiers touchés sont un catalogue et une recette : le sens du test ne doit pas changer, seul le texte du commentaire et de la docstring bouge).
- **Effort estimé** : complexité simple × durée courte.
- **Comment vous saurez que c'est fait** : une recherche du nom du produit sur l'arbre courant rend zéro occurrence ; la recette de la forge est verte ; le commit est publié en avance rapide après une porte de publication PASS.
- **Si ce n'est pas fait** : le nom reste public dans deux fichiers courants, et la règle du pilot (aucun nom de client ni de produit dans un dépôt publié) est tenue partout sauf ici.

## Ce que le pilot a déjà fait de son côté

- La mesure est faite et datée : diff entre `main` (`00097b6`) et la passe de réécriture du 05/09, trois remplacements, deux fichiers ; porte de publication PASS sur un clone de `main` seule (les 89 constats de ce matin vivaient dans une branche locale du poste du pilot, jamais poussée, supprimée depuis).
- Un paquet de sauvegarde de la forge existe hors dépôt chez le pilot (`c:\dev\_sauvegardes\digit-ai-forge-development-avant-filter-repo-20260905.bundle`) ; il n'a servi à rien et ne sert à rien ici.
- La question « la porte doit-elle juger aussi les noms de produits » est confiée à la forge des outils dans un lot séparé (règle C5) — ce lot-ci ne l'attend pas.
- Rien n'a été écrit dans le code de la forge ; la boîte `input\00-travaux\` existait depuis ce matin.

## Ce que le pilot NE demande PAS

- Pas de réécriture de l'historique de la forge : `main` est protégée, l'histoire publiée est verte au sens de la porte, et les mentions passées relèvent d'une autre décision.
- Pas de changement de la porte de publication : elle vit chez la forge des outils.
- Pas de modification du sens du catalogue ni de la recette : seul le texte d'un commentaire et d'une docstring change.

## Ordre recommandé

1. **Les trois remplacements d'abord**, parce qu'ils sont le seul geste du lot et qu'ils ne dépendent de rien.
2. **La recherche de contrôle et la recette ensuite**, parce qu'elles prouvent qu'il ne reste rien et que rien n'a bougé.

## Remise du compte rendu

À la clôture de votre run, un lot de retours `digit-ai-forge-development - RETOURS - <date><i>.md` (+ sidecar) remis dans `c:\dev\digit-ai-factory\input\00-retours\` dit ce qui a été fait, avec la preuve (recherche, recette, commit) — le pilot clôt l'item sur gains constatés.
