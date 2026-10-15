# Cible `fastapi-saas` — NON DISPONIBLE

Statut au 15/10/2026 (TF-1778, lot Produit-83) : **cible NON DISPONIBLE**. Le dossier `bricks/`
ne porte que `.gitkeep`. Aucune des briques que `copier.yml` décrit n'est écrite.

## Ce que la cible annonce et ce qui existe

| Brique | Annoncée par `copier.yml` | Ce qui existe dans cette forge |
|---|---|---|
| `multi-tenancy` | requise t0, `tenant_id` par ligne | une migration Alembic vide (`alembic revision --autogenerate -m "add tenancy"`), aucun modèle `Organization` |
| `rbac` | requise t0, Casbin | le paquet `casbin` ajouté (`uv add casbin`), aucune politique ni garde |
| `auth-sso` | requise t0, Authlib | le paquet `authlib` ajouté (`uv add authlib`), aucun flux de connexion |
| briques à la demande | billing, jobs, analytics, flags, emailing | le paquet de référence ajouté, rien d'autre |

Les actions réelles vivent dans `conductor/catalog.py`. Le scaffold (`conductor/scaffold.py`)
copie le gabarit amont `gh:fastapi/full-stack-fastapi-template`, pas ce dossier : les réponses
de `copier.yml` lui sont passées en `--data`, sans gabarit local qui les consomme.

## Ce que le produit fait

- Il ne compte sur aucune brique de t0 : multi-locataire, RBAC et SSO s'écrivent dans le
  produit, sous ses exigences, et se testent comme le reste de son code.
- Il ne cite pas cette cible comme source d'une brique dans son dossier d'architecture.
- `copier copy` sur ce dossier affiche l'avertissement `_message_before_copy` avant de copier.

## Quand la déclaration tombe

Le jour où une brique est écrite sous `bricks/`, le cas
`tests/test_scaffold.py::test_tf1778_une_cible_sans_briques_se_declare_non_disponible` rougit
tant que la mention NON DISPONIBLE reste dans `copier.yml` : la déclaration se retire avec la
première brique, dans le même commit.
