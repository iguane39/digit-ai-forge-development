# Migrations datées

Ce que les pages des deux fournisseurs annonçaient le 03/11/2026. Chaque ligne porte la phrase de la page, son adresse et la date de lecture. Une migration vieillit comme un modèle : rouvrir la page avant d'agir. Les identifiants de modèle (anciens et remplaçants) ne sont pas dans ce fichier mais dans [modeles-et-dates.md](modeles-et-dates.md), seul endroit où le skill peut les écrire ; la colonne « Détail des modèles » renvoie à ses lignes.

## OpenAI

| Migration | Échéance | Ce que dit la page | Adresse | Lu le | Détail des modèles |
|---|---|---|---|---|---|
| API Assistants vers Responses | arrêtée le 26/08/2026 | « The Assistants API was officially sunset on August 26, 2026, and is no longer available. » | https://developers.openai.com/api/docs/assistants/migration.md | 03/11/2026 | aucun |
| Chat Completions vers Responses | aucune échéance | « While Chat Completions remains supported, Responses is recommended for all new projects. » | https://developers.openai.com/api/docs/guides/migrate-to-responses.md | 03/11/2026 | aucun |
| Modèles d'image de première génération | 23/10/2026 pour le premier, 01/12/2026 pour trois autres | « On June 2, 2026, we notified developers using older GPT Image models of their deprecation and removal from the API on December 1, 2026. » | https://developers.openai.com/api/docs/deprecations.md | 03/11/2026 | lignes images d'OpenAI |
| Famille GPT-4 | 14/01/2027 | « On October 14, 2026, we notified developers using certain GPT-4 series models of their deprecation and removal from the API on January 14, 2027. » | https://developers.openai.com/api/docs/deprecations.md | 03/11/2026 | ligne du modèle léger de la famille |
| Objets d'invite réutilisables (`v1/prompts`) | 30/11/2026 | « Prompt creation will be de-emphasized beginning June 3, 2026, and `v1/prompts` is scheduled to shut down on November 30, 2026. » | https://developers.openai.com/api/docs/guides/text.md | 03/11/2026 | aucun |
| Agent Builder | 30/11/2026 | « the product is scheduled to shut down on November 30, 2026. » La page garde ChatKit disponible. | https://developers.openai.com/api/docs/guides/agent-builder.md | 03/11/2026 | aucun |
| Modèles de transcription | 26/02/2027 | La page des dépréciations annonce l'arrêt de quatre modèles de transcription, avec un remplaçant par modèle. | https://developers.openai.com/api/docs/deprecations.md | 03/11/2026 | paragraphe « Autres arrêts de la page d'OpenAI » |
| Modèles de synthèse vocale | 06/01/2027 | La page des dépréciations donne cette date pour trois familles de modèles de synthèse vocale. | https://developers.openai.com/api/docs/deprecations.md | 03/11/2026 | à lire sur la page |
| Anciens modèles de texte, dont celui de l'API Completions héritée | arrêtés le 28/09/2026 et le 23/10/2026 | La page de l'API Completions dit que ses modèles ont été arrêtés le 28/09/2026 ; la page des dépréciations liste d'autres arrêts au 23/10/2026. | https://developers.openai.com/api/docs/guides/completions.md | 03/11/2026 | aucun |

Une page d'OpenAI recommande, pour monter de version de modèle, de ne pas remplacer l'identifiant à l'aveugle : « Do not perform a blind model-string replacement » (guide « Upgrading to GPT-5.6 Sol », https://developers.openai.com/api/docs/guides/upgrading-to-gpt-5p6-sol.md, lu le 03/11/2026, cité par le catalogue du pilot). Ce guide est écrit pour un agent de code et demande un serveur MCP de documentation : on retient la règle de prudence, on n'exécute pas le guide ([SKILL.md](../SKILL.md)).

## Gemini

| Migration | Échéance | Ce que dit la page | Adresse | Lu le | Détail des modèles |
|---|---|---|---|---|---|
| Anciennes bibliothèques vers Google GenAI SDK | dépréciées depuis le 30/11/2025 | « The legacy libraries don't provide access to recent features (such as Live API and Veo) and are deprecated as of November 30th, 2025. » | https://ai.google.dev/gemini-api/docs/libraries.md.txt | 03/11/2026 | aucun |
| Guide de migration des bibliothèques | aucune échéance | « If you're using one of our legacy libraries, we strongly recommend you to migrate. » | https://ai.google.dev/gemini-api/docs/migrate.md.txt | 03/11/2026 | aucun |
| `generateContent` vers l'Interactions API | aucune échéance | « While `generateContent` remains fully supported, we recommend the Interactions API for all new development. » | https://ai.google.dev/gemini-api/docs/migrate-to-interactions.md.txt | 03/11/2026 | aucun |
| Schéma hérité de l'Interactions API | retrait annoncé le 08/06/2026, date passée | « The legacy schema will be removed on June 8, 2026. » La page demande l'en-tête `Api-Revision` pour gérer la migration. | https://ai.google.dev/gemini-api/docs/interactions-breaking-changes-may-2026.md.txt | 03/11/2026 | aucun |
| Réglages d'échantillonnage | aucune date | « `temperature`, `top_p`, and `top_k` are deprecated and ignored. In future model generations, supplying these parameters returns an HTTP 400 error. » | https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.6.md.txt | 03/11/2026 | aucun |
| Tour du modèle prérempli | refusé par les modèles récents | « Prefilling model turns is no longer supported. If the last non-empty turn in the request is a `model` turn, the API returns a `400` error. » | https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.6.md.txt | 03/11/2026 | aucun |
| Imagen vers les modèles d'image Gemini | arrêtés | « Imagen models are shut down. Use Nano Banana for image generation. » | https://ai.google.dev/gemini-api/docs/imagen.md.txt | 03/11/2026 | lignes images de Gemini |
| Modèles d'image Gemini | dates de 06/2026 à 03/2027 selon le modèle | La page des dépréciations donne un tableau par famille, avec un remplaçant ; ses dates sont « the earliest possible dates on which a model might be retired ». | https://ai.google.dev/gemini-api/docs/deprecations.md.txt | 03/11/2026 | lignes images de Gemini |
| Modèles Gemini 2.0 | arrêtés le 01/06/2026 | La page des dépréciations donne cette date de fermeture pour les quatre modèles de cette génération qu'elle liste. | https://ai.google.dev/gemini-api/docs/deprecations.md.txt | 03/11/2026 | aucun |

## Comment mener une migration

1. Rouvrir la page de la ligne concernée et noter ce qui a changé depuis le 03/11/2026.
2. Chercher l'usage dans le code : un `grep` de la bibliothèque, de l'adresse d'appel, des réglages retirés. Un identifiant de modèle littéral trouvé là est une anomalie à corriger par la table des modèles ([modeles-et-dates.md](modeles-et-dates.md)).
3. Écrire le test qui échoue sur l'ancien chemin, avec le double HTTP ([tester-sans-depenser.md](tester-sans-depenser.md)) : requête envoyée avec le réglage retiré, forme de réponse de l'ancienne API.
4. Corriger, puis vérifier que le test passe et que les fixtures qui citent la page migrée ont été rouvertes.
5. Ajouter ou modifier la ligne de la table des modèles avec sa date de relevé et son adresse ; ne jamais remplacer l'identifiant dans le code.
6. Un essai réel, avec une clé réelle, est une dépense : il se décide, se borne et se note par un humain. La migration est « corrigée par le test » avant d'être « constatée par l'essai ».
