"""Conductor — la couche d'orchestration mince de l'accélérateur SaaS Digit-AI.

Principe directeur (décision canonique 01 / NFR-1) : ce paquet n'implémente AUCUNE
logique métier des moteurs tiers (BMAD-METHOD, BAD, full-stack-fastapi-template,
design.md). Il les *séquence* et les *contraint* via cinq étapes A→E.

Voir ../../docs/architecture.md pour les contrats et le rôle de chaque module.
"""

__version__ = "0.0.0"
