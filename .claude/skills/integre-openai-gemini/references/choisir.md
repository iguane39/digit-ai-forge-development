# Choisir : API, bibliothèque, accès

Chaque citation donne sa page et sa date de lecture, le 03/11/2026. Les phrases entre guillemets sont celles des pages, en anglais, sans traduction. Les lignes « Avis du skill » sont des recommandations de ce skill, pas des faits cités. Aucun identifiant de modèle ici : ils vivent dans [modeles-et-dates.md](modeles-et-dates.md).

## 1. OpenAI : Responses ou Chat Completions

| Question | Ce que dit la page | Adresse | Lu le |
|---|---|---|---|
| Quelle API pour un nouveau projet ? | « While Chat Completions remains supported, Responses is recommended for all new projects. » | https://developers.openai.com/api/docs/guides/migrate-to-responses.md | 03/11/2026 |
| L'état est-il gardé côté serveur ? | « Responses are stored by default. Chat completions are stored by default for new accounts. To disable storage in either API, set `store: false`. » | https://developers.openai.com/api/docs/guides/migrate-to-responses.md | 03/11/2026 |
| Peut-on demander plusieurs générations ? | « Additionally, Chat Completions can return multiple parallel generations as `choices`, using the `n` parameter. The Responses API omits this parameter and returns only one generation. » | https://developers.openai.com/api/docs/guides/migrate-to-responses.md | 03/11/2026 |
| Et le cas audio ? | « For this audio-chat pattern, use Chat Completions with an audio-capable model. » | https://developers.openai.com/api/docs/guides/audio-chat-completions.md | 03/11/2026 |
| Et l'API Assistants ? | « The Assistants API was officially sunset on August 26, 2026, and is no longer available. » | https://developers.openai.com/api/docs/guides/migrate-to-responses.md | 03/11/2026 |
| Appels directs ou SDK d'agents ? | « Use the official OpenAI SDKs above for direct API requests. Use the Agents SDK when your application needs code-first orchestration for agents, tools, handoffs, guardrails, tracing, or sandbox execution. » | https://developers.openai.com/api/docs/libraries.md | 03/11/2026 |

Avis du skill. Un nouveau code appelle Responses. Chat Completions reste le bon choix quand le produit expose ou consomme un point d'accès à ce format (une passerelle, un outil tiers) ou pour le motif audio de la page ci-dessus ; changer de format est alors une décision avec un test, pas un réflexe. Un code qui lit `choices[0]` ne se convertit pas à la main sans le double HTTP de [tester-sans-depenser.md](tester-sans-depenser.md), parce que la forme de la réponse change.

## 2. Gemini : Interactions API ou generateContent

| Question | Ce que dit la page | Adresse | Lu le |
|---|---|---|---|
| Quelle interface pour un nouveau projet ? | « As of June 2026, it is Generally Available and the recommended interface for all new projects. » | https://ai.google.dev/gemini-api/docs/interactions-overview.md.txt | 03/11/2026 |
| Que devient `generateContent` ? | « While it is now considered legacy, the original `generateContent` API remains fully supported. » | https://ai.google.dev/gemini-api/docs/interactions-overview.md.txt | 03/11/2026 |
| Même position côté migration | « While `generateContent` remains fully supported, we recommend the Interactions API for all new development. » | https://ai.google.dev/gemini-api/docs/migrate-to-interactions.md.txt | 03/11/2026 |
| Que garde le serveur ? | « By default, the API stores all Interaction objects (`store=true`) » ; « Paid Tier: The system retains interactions for 55 days. » ; « Free Tier: The system retains interactions for 1 day. » | https://ai.google.dev/gemini-api/docs/interactions-overview.md.txt | 03/11/2026 |
| Peut-on ne rien garder ? | « If you don't want this, you can set `store=false` in your request. » | https://ai.google.dev/gemini-api/docs/interactions-overview.md.txt | 03/11/2026 |
| Le schéma de l'Interactions API a-t-il bougé ? | « The legacy schema will be removed on June 8, 2026. » | https://ai.google.dev/gemini-api/docs/interactions-breaking-changes-may-2026.md.txt | 03/11/2026 |
| Les réglages d'échantillonnage tiennent-ils ? | « `temperature`, `top_p`, and `top_k` are deprecated and ignored. In future model generations, supplying these parameters returns an HTTP 400 error. Remove these parameters from all requests. » | https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.6.md.txt | 03/11/2026 |
| Peut-on préremplir la réponse du modèle ? | « Prefilling model turns is no longer supported. If the last non-empty turn in the request is a `model` turn, the API returns a `400` error. » | https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.6.md.txt | 03/11/2026 |
| Quelle version d'API les SDK visent-ils ? | « The GenAI SDKs use `v1beta` by default to enable access to preview features. » | https://ai.google.dev/gemini-api/docs/api-versions.md.txt | 03/11/2026 |
| API Gemini ou plateforme Gemini ? | « Most developers should use the Gemini Developer API unless there is a need for specific enterprise controls. » | https://ai.google.dev/gemini-api/docs/migrate-to-cloud.md.txt | 03/11/2026 |

Avis du skill. Un nouveau code appelle l'Interactions API. Un code `generateContent` existant n'est pas en défaut : la page le dit pris en charge. Deux choses se vérifient avant tout changement de modèle côté Gemini : le code n'envoie plus les trois réglages d'échantillonnage, et il ne préremplit plus le dernier tour du modèle. La conservation de 55 jours des interactions est un fait de données personnelles : voir [cles-donnees-couts.md](cles-donnees-couts.md).

## 3. Plongements

| Fournisseur | Ce que dit la page | Adresse | Lu le |
|---|---|---|---|
| OpenAI | « To reduce the embedding's dimensions without losing its concept-representing properties, pass in the dimensions parameter » | https://developers.openai.com/api/docs/guides/embeddings.md | 03/11/2026 |
| Gemini | « Use the `output_dimensionality` parameter to control the size of the output embedding vector. » | https://ai.google.dev/gemini-api/docs/embeddings.md.txt | 03/11/2026 |

Règle du skill. La longueur d'un vecteur dépend du modèle et du réglage de dimension. Le produit range avec chaque vecteur l'identifiant du modèle, sa dimension et la date du calcul, lus de la table des modèles. Changer de modèle, c'est recalculer tous les vecteurs : deux modèles ne partagent pas d'espace de comparaison. Un dépôt d'agent conversationnel de l'étude déclare la bibliothèque `openai` et un modèle de plongement dans son `.env.example` : c'est le cas à traiter ainsi.

## 4. Images

| Fournisseur | Ce que dit la page | Adresse | Lu le |
|---|---|---|---|
| OpenAI | Le guide de génération d'images annonce l'arrêt du modèle d'image de première génération le 23/10/2026 ; l'identifiant et les modèles suivants sont dans [modeles-et-dates.md](modeles-et-dates.md). | https://developers.openai.com/api/docs/guides/image-generation.md | 03/11/2026 |
| Gemini | « Imagen models are shut down. Use Nano Banana for image generation. » | https://ai.google.dev/gemini-api/docs/imagen.md.txt | 03/11/2026 |

Les deux lignes disent la même chose : le modèle d'image d'hier s'arrête vite. Le code d'un produit ne nomme donc jamais le modèle d'image, et la table des modèles porte la date d'arrêt annoncée. Les arrêts datés sont dans [modeles-et-dates.md](modeles-et-dates.md) et [migrations.md](migrations.md).

## 5. Bibliothèques officielles

Versions lues le 03/11/2026 par `curl -s https://api.github.com/repos/<organisation>/<dépôt>/releases/latest` (anonyme, à défaut le dernier tag), rapportées par le catalogue du pilot, puis recoupées le même jour avec la liste `bibliotheques` de `references\MODELES-TIERS.json` du pilot (mêmes versions et mêmes dates pour les lignes reprises ci-dessous) ; non rejouées sur GitHub ici. Une version se relit à l'installation : elle sert à repérer l'ordre de grandeur et les bibliothèques abandonnées, pas à épingler.

OpenAI. Source : https://developers.openai.com/api/docs/libraries.md, lue le 03/11/2026.

| Bibliothèque | Langage | Dépôt | Version | Publiée le |
|---|---|---|---|---|
| SDK OpenAI | TypeScript, JavaScript | https://github.com/openai/openai-node | v7.47.0 | 2026-10-31 |
| SDK OpenAI | Python | https://github.com/openai/openai-python | v3.42.1 | 2026-11-01 |
| Client officiel (paquet NuGet OpenAI) | C#, .NET | https://github.com/openai/openai-dotnet | OpenAI_2.14.0 | 2026-09-15 |
| openai-java (« API helper », bêta selon la page) | Java | https://github.com/openai/openai-java | v4.96.0 | 2026-11-01 |
| openai-go (« API helper », bêta selon la page) | Go | https://github.com/openai/openai-go | v3.91.1 | 2026-11-01 |
| SDK OpenAI | Ruby | https://github.com/openai/openai-ruby | v0.115.1 | 2026-11-01 |
| CLI `openai` | Go (ligne de commande) | https://github.com/openai/openai-cli | v1.47.0 | 2026-10-31 |
| Agents SDK | TypeScript | https://github.com/openai/openai-agents-js | @openai/agents-extensions@0.21.0 | 2026-10-20 |
| Agents SDK | Python | https://github.com/openai/openai-agents-python | v0.24.0 | 2026-10-15 |
| tiktoken (comptage de jetons) | Python | https://github.com/openai/tiktoken | 0.14.0 | 2026-08-17 |

Les autres dépôts de l'organisation que la page liste (évaluation, apprentissage par renforcement, orchestration éducative) ne sont pas des SDK de l'API et ne sont pas repris ici. Les bibliothèques de Microsoft pour Azure et celles de la communauté sont listées par la page ; la page dit des secondes que OpenAI ne vérifie ni leur justesse ni leur sécurité.

Gemini. Source : https://ai.google.dev/gemini-api/docs/libraries.md.txt, lue le 03/11/2026. Elle recommande le Google GenAI SDK et dit des anciennes bibliothèques qu'elles « are deprecated as of November 30th, 2025 ».

| Bibliothèque | Langage | Dépôt | Version | Publiée le | État |
|---|---|---|---|---|---|
| google-genai | Python | https://github.com/googleapis/python-genai | v2.34.0 | 2026-10-29 | recommandée |
| @google/genai | JavaScript, TypeScript | https://github.com/googleapis/js-genai | v2.32.0 | 2026-10-29 | recommandée |
| google.golang.org/genai | Go | https://github.com/googleapis/go-genai | v1.77.0 | 2026-10-29 | recommandée |
| google-genai (com.google.genai) | Java | https://github.com/googleapis/java-genai | v1.80.0 | 2026-10-29 | recommandée |
| Google.GenAI | C# | https://github.com/googleapis/dotnet-genai | Google.GenAI-v1.28.0 | 2026-10-29 | recommandée |
| google-generativeai | Python | https://github.com/google-gemini/deprecated-generative-ai-python | v0.8.6 | 2025-12-16 | dépréciée |
| @google/generative-ai | JavaScript, TypeScript | https://github.com/google-gemini/deprecated-generative-ai-js | v0.24.1 | 2025-04-29 | dépréciée |
| github.com/google/generative-ai-go | Go | https://github.com/google/generative-ai-go | v0.20.1 | 2025-05-02 | dépréciée |
| google_generative_ai | Dart, Flutter | https://pub.dev/packages/google_generative_ai | 0.4.7 | 2025-04-17 | dépréciée, la page recommande Genkit Dart ou Firebase AI Logic |
| firebase_ai | Dart, Flutter | https://pub.dev/packages/firebase_ai | 5.1.0 | 2026-10-23 | remplaçant recommandé |

Le tableau de la page orthographie le paquet JavaScript hérité `@google/generativeai`, le catalogue du pilot `@google/generative-ai` (dépôt `google-gemini/generative-ai-js`, redirigé vers le dépôt `deprecated-`). Les deux désignent la bibliothèque dépréciée : avant de chercher ou de retirer ce paquet, relire `package.json` pour son nom exact. Les bibliothèques héritées pour Swift et Android sont aussi dépréciées (même page). Le Java n'avait pas de bibliothèque héritée de Google, selon la page.

Règle du skill. Un produit qui déclare une bibliothèque dépréciée en dépendance la remplace avant d'ajouter une fonction : la page dit que les anciennes bibliothèques « don't provide access to recent features (such as Live API and Veo) » (https://ai.google.dev/gemini-api/docs/libraries.md.txt, lu le 03/11/2026). Les dépendances s'épinglent à la version installée, relevée au moment de l'installation.

## 6. REST direct ou bibliothèque

Le fait. La page des SDK d'OpenAI nomme la quatrième voie : « your own preferred HTTP client » (https://developers.openai.com/api/docs/libraries.md, lu le 03/11/2026). L'étude du pilot relève un produit qui appelle les deux fournisseurs en REST par `httpx`, derrière un contrat unique partagé avec son fournisseur Claude, et un autre produit dont la passerelle parle le format Chat Completions.

Avis du skill :

- Bibliothèque officielle par défaut : elle porte les nouveautés et les types, et suit les changements de schéma que les pages annoncent (voir les deux tableaux ci-dessus).
- REST direct justifié quand le produit a déjà une frontière de fournisseur à contrat unique et n'emploie qu'une fonction étroite, la génération de texte. Il en prend alors la charge : chaque changement de schéma, comme celui du 08/06/2026 de l'Interactions API, devient une correction à faire à la main, et le double HTTP de [tester-sans-depenser.md](tester-sans-depenser.md) est le seul filet.
- Dans les deux cas, le fournisseur se cache derrière une interface du produit (entrée : texte et réglages métier ; sortie : texte, jetons comptés, motif d'arrêt). Les identifiants de modèle et les réglages propres à un fournisseur ne sortent pas de son implémentation.

## 7. Azure OpenAI

Ce que les sources du 03/11/2026 établissent :

| Fait | Source | Adresse | Lu le |
|---|---|---|---|
| Microsoft maintient des bibliothèques pour .NET, JavaScript, Java et Go, « compatible with both the OpenAI API and Azure OpenAI services » | page des SDK d'OpenAI | https://developers.openai.com/api/docs/libraries.md | 03/11/2026 |
| OpenAI ne publie pas ces bibliothèques ; le catalogue du pilot les exclut de ses tableaux | catalogue du pilot | https://developers.openai.com/api/docs/libraries.md | 03/11/2026 |
| Un point d'accès régional d'OpenAI se joint depuis Azure sans passer par l'Internet public : « OpenAI Private Link lets Azure workloads reach regional OpenAI API endpoints through Azure Private Link instead of connecting directly to public API endpoints. » C'est l'API d'OpenAI, pas le service Azure OpenAI. | page Private Link | https://developers.openai.com/api/docs/guides/private-link.md | 03/11/2026 |
| La commande d'audit d'un déploiement Azure OpenAI de forge-audit (CTL-D14-04) envoie un `curl -X POST` avec l'en-tête `api-key` ; un produit de l'étude lit des variables `AZURE_OPENAI_*` | étude du pilot, sections 2 et 4 | `Digit-AI - Étude - Competences OpenAI et Gemini - 20261103l` | 03/11/2026 |

Non lu le 03/11/2026, à relire sur la documentation de Microsoft avant d'écrire l'appel : la forme de l'adresse d'un déploiement, la version d'API à passer, la façon dont le nom d'un déploiement remplace l'identifiant de modèle, l'authentification par identité plutôt que par clé, le calendrier d'arrêt des modèles côté Azure, qui peut différer de celui d'OpenAI. Tant que ce n'est pas relu, un produit Azure ne reprend pas les dates de [modeles-et-dates.md](modeles-et-dates.md) comme les siennes.

Règle du skill. La clé d'un déploiement Azure suit les mêmes règles que toute clé : variable d'environnement, jamais dans une ligne de commande ni dans un journal ([cles-donnees-couts.md](cles-donnees-couts.md)). Un appel de vérification payant chez un client ne se lance pas sans accord de ce client.
