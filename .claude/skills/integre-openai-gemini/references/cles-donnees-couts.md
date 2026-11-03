# Clés, données personnelles, coûts

Mêmes conventions que [choisir.md](choisir.md) : chaque citation porte son adresse et sa date de lecture, le 03/11/2026 ; « Règle du skill » désigne une recommandation de ce skill, pas un fait cité.

## 1. Les clés

| Fait | Ce que dit la page | Adresse | Lu le |
|---|---|---|---|
| OpenAI : la clé s'exporte en variable d'environnement | La page des SDK demande d'exporter la clé dans la variable `OPENAI_API_KEY` | https://developers.openai.com/api/docs/libraries.md | 03/11/2026 |
| Gemini : variable recommandée | « Set the environment variable `GEMINI_API_KEY` or `GOOGLE_API_KEY`. » ; « If both are set, `GOOGLE_API_KEY` takes precedence. » | https://ai.google.dev/gemini-api/docs/api-key.md.txt | 03/11/2026 |
| Gemini : clé en dur dans le code | « You can pass the API key explicitly when initializing the client. Only do this if you cannot use environment variables. » | https://ai.google.dev/gemini-api/docs/api-key.md.txt | 03/11/2026 |
| Gemini : dépôt | « Never check API keys into source control systems like Git. » | https://ai.google.dev/gemini-api/docs/api-key.md.txt | 03/11/2026 |
| Gemini : navigateur et mobile | « Never expose keys client-side in production » ; « To secure client-side apps, run a backend proxy server to make the actual API calls. » | https://ai.google.dev/gemini-api/docs/api-key.md.txt | 03/11/2026 |
| Gemini : clés non restreintes | « The Gemini API rejects requests from unrestricted standard keys. » ; depuis le 28/05/2026, les nouvelles clés créées dans Google AI Studio sont des clés d'autorisation | https://ai.google.dev/gemini-api/docs/api-key.md.txt | 03/11/2026 |

Règles du skill :

- Une clé vit dans une variable d'environnement du processus qui appelle. Jamais dans une ligne de commande : un argument de processus se lit dans l'historique du shell et dans la liste des processus. L'étude du pilot du 03/11/2026 relève ce défaut dans une commande d'audit qui envoie un `curl -X POST` avec l'en-tête `api-key: <key>` : la clé finit dans l'historique (item TF-2112, décision D-163). Une vérification se fait par un petit client qui lit la variable d'environnement, pas par une commande qui porte la clé dans ses arguments.
- Le fichier d'exemple du produit (`.env.example`) ne porte que les noms de variables, jamais une valeur. Le fichier `.env` est ignoré par git, et il ne transite jamais dans la Factory (ni lu, ni copié, ni déplacé par un agent).
- Les secrets d'un produit en production vivent dans le coffre de son hébergeur, pas dans un fichier de configuration ; la page de Gemini le dit : « For production, store your keys in a secure secret store » (https://ai.google.dev/gemini-api/docs/api-key.md.txt, lu le 03/11/2026).
- Une clé par environnement (développement, recette, production) et par produit : une fuite se révoque sans arrêter le reste.
- Une clé qui a touché un dépôt, un journal ou une conversation est considérée fuitée : on la révoque chez le fournisseur, on en crée une autre, on corrige l'historique si le dépôt est partagé. La Factory contrôle les secrets en dur par `conductor/gates/ai_antipatterns_gate.py` (cette forge) et par le contrôle `oracle-secrets` de `quality-oracles`.
- Un produit lit la clé au démarrage ou à la première utilisation et s'arrête avec un message qui nomme la variable manquante, sans afficher la valeur ni un préfixe.
- Le produit qui appelle l'API depuis un navigateur ou une application mobile passe par un serveur à lui. La clé n'est jamais envoyée au client.

## 2. Données personnelles envoyées à un tiers

Le cas de l'étude : un produit (Produit-12) envoie des courriels à classer à un fournisseur d'IA ; la fiche `expert-conformite-rgpd-ia` d'`experts-forge` couvre le cadre juridique de l'IA sans nommer ces fournisseurs. Ce skill ajoute ce que les pages disent des fournisseurs.

| Fait | Ce que dit la page | Adresse | Lu le |
|---|---|---|---|
| OpenAI : les réponses sont gardées par défaut | « Responses are stored by default. Chat completions are stored by default for new accounts. To disable storage in either API, set `store: false`. » | https://developers.openai.com/api/docs/guides/migrate-to-responses.md | 03/11/2026 |
| OpenAI : organisations à rétention nulle | « For ZDR organizations, OpenAI enforces `store: false` automatically. » | https://developers.openai.com/api/docs/guides/migrate-to-responses.md | 03/11/2026 |
| Gemini : les interactions sont gardées par défaut | « By default, the API stores all Interaction objects (`store=true`) » ; 55 jours au palier payant, 1 jour au palier gratuit | https://ai.google.dev/gemini-api/docs/interactions-overview.md.txt | 03/11/2026 |
| Gemini : ne rien garder | « you can set `store=false` in your request » | https://ai.google.dev/gemini-api/docs/interactions-overview.md.txt | 03/11/2026 |

Règles du skill :

- Ne pas envoyer ce qui ne sert pas. Un produit qui classe des courriels envoie le texte nécessaire au classement, pas les adresses ni les pièces jointes qu'il n'exploite pas. Quand c'est possible, il remplace les noms par des jetons avant l'envoi et les rétablit à la réponse.
- Poser la rétention au plus bas par défaut (`store: false` côté OpenAI, `store=false` côté Gemini) dès que la requête porte une donnée personnelle, et le dire dans le registre du produit. Gemini signale une incompatibilité : l'option `store=false` ne se combine pas avec l'exécution en arrière-plan (même page).
- Journaliser chaque envoi sans son contenu : rôle, identifiant du modèle lu de la table, taille, date, statut. Le contenu d'une requête est une donnée personnelle de plus à protéger.
- Le palier gratuit et le palier payant n'ont pas la même rétention (Gemini, ci-dessus) ; les conditions d'usage des données par chaque fournisseur ne sont pas dans les pages lues le 03/11/2026. Une donnée personnelle ne va donc pas à un palier dont on n'a pas lu les conditions.
- La base légale, le contrat de sous-traitance, le lieu de traitement et l'information des personnes sont des décisions humaines du responsable du produit. Le skill les nomme, il ne les tranche pas. Pour un accès privé depuis Azure, voir la ligne Private Link de [choisir.md](choisir.md), section 7 ; pour un déploiement Azure OpenAI, la documentation de Microsoft n'est pas lue.

## 3. Le suivi des coûts

| Fait | Ce que dit la page | Adresse | Lu le |
|---|---|---|---|
| OpenAI : alertes de dépense | « Spend alerts notify your team when monthly usage reaches a threshold, but they don't stop API requests or enforce a spending cap. » | https://developers.openai.com/api/docs/guides/terraform/rate-limits-and-spend.md | 03/11/2026 |
| OpenAI : plafond mensuel | La page des API d'administration décrit un point d'accès pour créer ou remplacer le plafond mensuel strict de l'organisation (section « Set an organization spend limit ») | https://developers.openai.com/api/docs/guides/admin-apis.md | 03/11/2026 |
| OpenAI : traitement différé moins cher | « send asynchronous groups of requests with 50% lower costs » | https://developers.openai.com/api/docs/guides/batch.md | 03/11/2026 |
| Gemini : traitement différé | « The target turnaround time is 24 hours, but in majority of cases, it is much quicker. » | https://ai.google.dev/gemini-api/docs/batch-api.md.txt | 03/11/2026 |
| Gemini : palier flexible | « The Gemini Flex API is an inference tier that offers a 50% cost reduction compared to standard rates » | https://ai.google.dev/gemini-api/docs/generate-content/flex-inference.md.txt | 03/11/2026 |

Règles du skill :

- Aucun prix dans le code ni dans ce skill : un tarif change et se lit à la date de l'appel. Si le produit chiffre ses coûts, il tient une table de tarifs datée et sourcée, comme la table des modèles ([modeles-et-dates.md](modeles-et-dates.md)).
- Le produit journalise pour chaque appel : rôle, identifiant du modèle, nombre de jetons d'entrée et de sortie tels que le fournisseur les rend, durée, statut. C'est la matière d'un suivi par client ou par fonction. L'étude relève un produit (Produit-82) qui a déjà un export de refacturation : le suivre d'abord s'il existe.
- Deux garde-fous distincts : l'alerte, qui prévient, et le plafond, qui coupe. La page d'OpenAI dit que l'alerte ne bloque rien. Un produit qui doit rester sous un budget le tient dans son propre code (budget par rôle ou par client, coupure au dépassement) et demande à l'humain de poser le plafond chez le fournisseur.
- Les tarifs réduits du traitement différé conviennent au non urgent (reclassement en lot, plongements d'un corpus) ; une réponse attendue par une personne passe par l'appel direct.
- En test, la dépense est nulle ([tester-sans-depenser.md](tester-sans-depenser.md)). Un essai réel, avec une clé réelle, se décide, se borne et se paie par un humain ; la Factory n'en lance pas.
