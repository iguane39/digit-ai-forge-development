# Modèles et dates : une donnée, pas du code

Seul fichier du skill autorisé à écrire un identifiant de modèle. `scripts/controle-modeles.mjs` refuse un identifiant ou un prix partout ailleurs dans le skill.

## La règle

Aucun identifiant de modèle ni aucun prix dans le code d'un produit, ni dans ce skill. Un identifiant se lit à deux endroits.

1. Le référentiel daté du pilot, `references\MODELES-TIERS.json` (item TF-2109, schéma `pilot/modeles-tiers@1`). Il a été créé le 03/11/2026 à 17:11, en parallèle de ce skill : le premier `ls` de ce travail, peu après 17:00, rendait « No such file or directory ». Pour chaque fournisseur (`openai`, `gemini`), sa liste `modeles` donne un identifiant, un état (`courant`, `deprecie` ou `arrete`), la date d'arrêt, le remplaçant et la citation de la page ; il nomme pour juge `oracles/oracle-modeles-tiers.mjs`. Le lire avant de reporter une ligne : il se relit à la main, il ne se complète jamais de mémoire.
2. Une table éditable du produit, alimentée depuis ce référentiel par la session de la Factory qui ouvre le run. Le produit ne lit pas le pilot à l'exécution : il lit sa propre table.

Si la ligne cherchée manque au référentiel ou s'il est périmé, la source est la page du fournisseur du jour (adresses ci-dessous), reportée dans la table avec sa date de relevé.

## La table du produit

| Colonne | Contenu |
|---|---|
| `role` | l'usage métier : génération de texte, plongement, image. Le code demande un rôle, jamais un identifiant. |
| `fournisseur` | `openai`, `gemini`, ou `azure-openai` si le produit passe par Azure. |
| `identifiant` | la valeur reportée du référentiel ou de la page, jamais saisie de mémoire. |
| `releve_le` | la date de lecture de la source. |
| `source` | l'adresse de la page qui porte l'identifiant. |
| `arret_annonce` | la date d'arrêt annoncée, vide si aucune. |
| `remplacant` | le remplaçant annoncé, vide si aucun. |
| `statut` | `courant`, `deprecie` ou `arrete`, comme les états du référentiel du pilot. |

Ce que le produit en fait :

- Le code appelle `modele_pour(role)`. Une ligne `arrete` lève une erreur qui nomme le rôle et la source, au lieu d'envoyer un appel que le fournisseur refusera.
- Une ligne dont `arret_annonce` approche se signale au journal. Le préavis est un paramètre du produit, pas une valeur de ce skill.
- La table se peuple par une migration datée (le playbook de la forge exempte les migrations de peuplement) et se modifie par une nouvelle ligne ou une mise à jour datée, jamais par un littéral dans le code.
- Le test du produit contient le grep du playbook (`docs/run-playbook.md`, « Données volatiles en base ») et, mieux, `controle-modeles.mjs <dossier du code> --autorise <fichier de peuplement>`, qui élargit le motif aux familles d'identifiants d'OpenAI et de Gemini.
- Les dates d'arrêt de Gemini sont, selon la page, « the earliest possible dates on which a model might be retired » (https://ai.google.dev/gemini-api/docs/deprecations.md.txt, lu le 03/11/2026) : une date lointaine n'est pas une garantie.

## Arrêts observés le 03/11/2026 (un constat daté, pas une référence)

Cette table existe pour que le skill puisse dire quels cas le parc rencontre. Elle vieillit : la source qui fait foi est le référentiel du pilot, puis la page. Dates d'arrêt lues sur les pages du fournisseur le 03/11/2026, puis recoupées le même jour avec `MODELES-TIERS.json` : identifiants, états, dates d'arrêt et remplaçants de ces lignes y sont identiques (recoupement fait par script de lecture, hors skill).

| Fournisseur | Identifiant | Arrêt annoncé | Remplaçant annoncé | Où le parc l'emploie (étude du pilot, 03/11/2026) | Adresse |
|---|---|---|---|---|---|
| OpenAI | `gpt-4o-mini-2024-07-18` | 14/01/2027 | `gpt-6-luna` | épinglé dans la configuration de Produit-82 | https://developers.openai.com/api/docs/deprecations.md |
| OpenAI | `gpt-image-1` | arrêté le 23/10/2026 | `gpt-image-2.5-sunburst` ou `gpt-image-2.5-flare` | non relevé dans le parc par l'étude | https://developers.openai.com/api/docs/deprecations.md |
| OpenAI | `gpt-image-1-mini`, `gpt-image-1.5`, `chatgpt-image-latest` | 01/12/2026 | `gpt-image-2.5-sunburst` ou `gpt-image-2.5-flare` | non relevé dans le parc par l'étude | https://developers.openai.com/api/docs/deprecations.md |
| Gemini | `gemini-3.1-flash-image-preview`, `gemini-3-pro-image-preview` | arrêtés le 25/06/2026 | `gemini-nano-banana-2.1`, `gemini-3-pro-image` | replis du script de génération d'images de forge-design | https://ai.google.dev/gemini-api/docs/deprecations.md.txt |
| Gemini | `gemini-2.5-flash-image` | 15/03/2027 | `gemini-3.1-flash-lite-image` | repli du même script | https://ai.google.dev/gemini-api/docs/deprecations.md.txt |
| Gemini | `gemini-3.1-flash-image` | déprécié le 28/05/2026, aucune date d'arrêt | `gemini-nano-banana-2.1` | défaut de forge-design et d'un dépôt retail | https://ai.google.dev/gemini-api/docs/deprecations.md.txt |
| Gemini | `text-embedding-004` | arrêté le 14/01/2026 | `gemini-embedding-2` | non relevé dans le parc par l'étude | https://ai.google.dev/gemini-api/docs/deprecations.md.txt |

Autres arrêts de la page d'OpenAI qui touchent des familles entières, lus le 03/11/2026 sur https://developers.openai.com/api/docs/deprecations.md : les modèles de transcription (`whisper-1` et trois autres) le 26/02/2027 ; des instantanés plus anciens de `gpt-5`, de `o3` et de leurs variantes le 11/12/2026. Aucun modèle de plongement d'OpenAI n'y figure comme arrêté : la page ne cite le modèle de plongement courant que comme remplaçant d'anciens modèles de 2024. Ce constat vaut pour la page du 03/11/2026 seulement.

## Migrations qui nomment des modèles

Les arrêts de modèles d'images, de transcription et de raisonnement ci-dessus sont les migrations de [migrations.md](migrations.md) qui touchent des identifiants. Ils vivent ici parce que ce fichier est le seul à pouvoir les écrire.
