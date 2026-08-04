"""Shim ``gh`` → ``az`` : rend le sprint ``/bad`` provider-agnostique sur Azure DevOps.

BAD (vendorisé, jamais forké) pilote son pipeline avec la CLI ``gh`` (GitHub only). Sur un dépôt
Azure DevOps, le superviseur place un exécutable ``gh`` (ce shim) en tête de PATH ; il traduit la
surface réelle de BAD (``pr list/view/checks/diff/merge``, ``issue list/create``, ``auth``,
``run view``) vers ``az repos``/``az account``, en émettant le **schéma JSON attendu par BAD**.

GitHub : aucun shim (PATH normal, ``gh`` réel), strictement inchangé.
"""

from conductor.harness.gh_shim.translate import ShimResult, translate

__all__ = ["ShimResult", "translate"]
