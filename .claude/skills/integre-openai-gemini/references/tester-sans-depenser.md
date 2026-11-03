# Tester sans dépenser

Un appel à OpenAI ou à Gemini coûte de l'argent et dépend d'un service tiers. Une suite de tests qui l'appelle coûte à chaque lancement, échoue quand le réseau tombe et oblige à laisser une clé dans l'environnement de test. La règle de la Factory interdit l'appel payant sans décision humaine : le test la tient par construction.

## Origine

L'étude du pilot du 03/11/2026 relève qu'un produit (Produit-12) appelle les deux fournisseurs en REST par `httpx`, au même contrat que son fournisseur Claude, et teste ses fournisseurs sans appel réel (`backend/tests/test_mutants_fournisseurs.py:60`, tableau 3.5 de l'étude). Ce fichier décrit le principe, pas son code : aucun code de produit n'est repris ici. Le constat de forge-tests qui exigera un bouchon est l'item TF-2110, non écrit au 03/11/2026.

## Les cinq propriétés d'un bon double

1. Il remplace le réseau, pas votre code. Le produit exécute son vrai client et sa vraie sérialisation ; seul le transport est simulé. Le test vérifie la requête envoyée (adresse, en-têtes sans la clé, corps) et la lecture de la réponse.
2. Une requête de trop fait échouer le test. Un double qui laisse passer les requêtes imprévues vers le réseau réel finit par appeler le fournisseur le jour où quelqu'un ajoute un appel.
3. Aucune clé n'existe pendant la suite. Le test supprime les variables de clé de l'environnement et prouve que le client sans clé s'arrête avec un message qui ne reproduit rien d'une clé.
4. Les réponses fabriquées viennent d'une page de référence. Chaque fixture cite l'adresse de la page du fournisseur et sa date de lecture, de façon qu'une migration (voir [migrations.md](migrations.md)) sache quelles fixtures rouvrir.
5. Chaque fournisseur passe la même suite de contrat. Le produit a une frontière de fournisseur (texte et réglages en entrée, texte, jetons comptés et motif d'arrêt en sortie) ; la même série de cas s'applique à chaque implémentation, alimentée par le double de son fournisseur.

## Cas à jouer, par fournisseur

- réponse normale, lue jusqu'au texte et au décompte de jetons ;
- limite de débit et erreur serveur : reprise bornée en nombre et en durée, puis erreur claire ;
- requête refusée (code 400) parce qu'un réglage n'est plus accepté : le cas des réglages d'échantillonnage et du tour du modèle prérempli que Gemini refuse depuis ses modèles récents ([choisir.md](choisir.md), section 2) ;
- réponse tronquée ou vide, avec son motif d'arrêt ;
- délai dépassé ;
- flux coupé en route, si le produit lit en flux ;
- ligne de la table des modèles à l'état `arrete` : l'erreur se lève avant tout appel ([modeles-et-dates.md](modeles-et-dates.md)) ;
- données personnelles : la requête fabriquée par le test ne contient que ce que le produit a décidé d'envoyer ([cles-donnees-couts.md](cles-donnees-couts.md)).

## Un double HTTP en Python

Le principe tient en quinze lignes avec `httpx.MockTransport`. L'identifiant de modèle vient de la table du produit, ici d'une fonction `modele_pour`.

```python
import httpx


def double_fournisseur(reponses):
    """Un client HTTP dont chaque requête consomme la réponse suivante ; une requête de trop échoue."""
    vues = []
    file = list(reponses)

    def repondre(requete):
        vues.append(requete)
        if not file:
            raise AssertionError(f"requête imprévue : {requete.method} {requete.url}")
        return file.pop(0)

    return httpx.Client(transport=httpx.MockTransport(repondre)), vues
```

```python
import pytest


@pytest.fixture(autouse=True)
def sans_cle(monkeypatch):
    """Aucune clé de fournisseur pendant la suite."""
    import os

    for nom in list(os.environ):
        if nom in ("OPENAI_API_KEY", "GEMINI_API_KEY") or nom.startswith("AZURE_OPENAI_"):
            monkeypatch.delenv(nom, raising=False)
```

Un test type : fabriquer `httpx.Response(200, json=<corps de la page de référence>)`, passer le client au produit, vérifier le texte lu, vérifier que `vues` contient une seule requête et que son en-tête d'autorisation vient du produit et pas de l'environnement.

Le même principe en Node : injecter la fonction `fetch` du produit.

```js
export function doubleFetch(reponses) {
  const vues = [];
  const file = [...reponses];
  const fetchDouble = async (url, options = {}) => {
    vues.push({ url: String(url), options });
    if (file.length === 0) throw new Error(`requête imprévue : ${url}`);
    const { statut = 200, corps } = file.shift();
    return new Response(JSON.stringify(corps), {
      status: statut,
      headers: { 'content-type': 'application/json' },
    });
  };
  return { fetchDouble, vues };
}
```

Ces trois extraits ont été rejoués le 03/11/2026 sur des cas à double sens (réponse prévue consommée, requête de trop refusée) : voir `scripts/self-test.mjs`, cas « extraits de tester-sans-depenser ».

Avec une bibliothèque officielle, le même double passe par le client HTTP que la bibliothèque accepte en paramètre. Que le SDK choisi en accepte un n'est pas établi par les pages lues le 03/11/2026 : à vérifier dans la documentation de la bibliothèque avant de choisir cette voie ; sinon, faire passer le produit par REST direct ([choisir.md](choisir.md), section 6) ou isoler le SDK derrière la frontière et doubler la frontière.

## Enregistrements

Un enregistrement est une réponse réelle gardée pour être rejouée. Il se prend une fois, par une personne qui a le droit de dépenser, jamais par la suite de tests. Il se range sans clé ni en-tête d'autorisation, sans donnée personnelle, avec la date de la prise, l'adresse de la page de référence et le jeu de réglages qui l'a produit. Il est périmé le jour où une migration touche l'API ou le modèle : la date de la prise le dit.

## Ce que le double ne prouve pas

Qu'un modèle répond bien, que le coût réel reste dans le budget, que le fournisseur n'a pas changé son schéma depuis la fixture. Cela se prouve par un essai réel borné, décidé et payé par un humain, noté avec sa date. Le double garantit le reste, tous les jours, pour rien.
