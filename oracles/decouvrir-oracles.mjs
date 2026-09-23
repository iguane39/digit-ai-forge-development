#!/usr/bin/env node
/**
 * decouvrir-oracles.mjs — les oracles de forge-development, LUS SUR LE DISQUE, jamais recopiés
 * d'une liste (TF-1319, 23/09/2026 : temps 2 du verdict O3 de l'étude du pilot du 19/08/2026 sur
 * le méta-oracle d'enclenchement).
 *
 * POURQUOI. Un run consigne au ledger une entrée `oracles_verdict` par oracle qui a tourné (forme
 * canonique TF-0385). Pour dire lesquels MANQUENT, le juge du pilot doit savoir ce que chaque forge
 * mobilisée porte. L'étude du 19/08 comptait zéro oracle ici : elle cherchait le préfixe `oracle-`,
 * et cette forge appelle les siens des GATES — « la doctrine devient oracle exécutable », disent
 * leurs en-têtes. Mesuré le 23/09/2026 : `conductor/gates/` porte 11 modules `*_gate.py`, dont 9
 * se lancent seuls et rendent un verdict (`python -m conductor.gates.<nom>`, PASS/FAIL) ; aucun
 * point d'entrée ne les énumère — le superviseur en importe 2, la recette locale en lance 2, la CI
 * en nomme 4, chacun par son nom.
 *
 * LA RÈGLE, EN DEUX PARTIES, TOUTES DEUX LUES SUR LE DISQUE :
 *   · un module `digit-ai-forge-development/conductor/gates/*_gate.py` qui porte son propre point
 *     d'entrée (`if __name__ == "__main__":`) — un gate qui se lance seul rend un verdict qu'un run
 *     peut consigner sous son nom. Ceux qui n'en portent pas (`code_gate` délègue à la CI du
 *     template, `regression_gate` est évalué par le superviseur) sont NOMMÉS au non_juge, jamais
 *     tus : ils jugent, mais sous le nom d'un autre ;
 *   · tout fichier nommé `oracle-<nom>.mjs|.cjs|.js` ou `oracle[-_]<nom>.py` du dépôt, hors
 *     dépendances, caches, `vendor`, archives, `fixtures` et entrants — la règle commune du parc,
 *     pour qu'un oracle déposé demain sous ce nom soit vu sans qu'on l'annonce.
 *
 * POURQUOI UN SCRIPT NODE DANS UNE FORGE PYTHON. Le contrat de découverte est COMMUN au parc et son
 * juge est un oracle Node du pilot : une entrée au même chemin et dans le même langage partout
 * évite au juge de tenir une table des forges et de leurs interpréteurs. Node est un prérequis
 * bloquant du poste (`bootstrap.mjs` du pilot). La recette, elle, suit les conventions d'ici.
 *
 * LE CONTRAT, COMMUN AU PARC (`digit-ai/decouverte-oracles@1`, CONTRAT-INTERFACE.md §3 du pilot) :
 *   node oracles/decouvrir-oracles.mjs [--racine <dossier>]
 *   stdout : { contrat, forge, racine, regle, oracles: [{ nom, chemin }], non_juge: [] }
 *   exit 0 : découverte faite — une liste vide est un résultat, et elle se lit comme telle ;
 *   exit 2 : racine illisible, motif dit. Jamais d'exit 1 : découvrir n'est pas juger.
 * Ce script ne lance aucun gate et n'écrit rien.
 *
 * Recette à double sens : `digit-ai-forge-development/tests/test_decouvrir_oracles.py` (pytest).
 */
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { basename, dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const CONTRAT = "digit-ai/decouverte-oracles@1";
export const FORGE = "digit-ai-forge-development";
export const DOSSIER_GATES = join("digit-ai-forge-development", "conductor", "gates");
export const REGLE = "tout module `digit-ai-forge-development/conductor/gates/*_gate.py` qui porte son propre point "
  + "d'entrée (`if __name__ == \"__main__\":`), plus tout fichier `oracle-<nom>.(mjs|cjs|js)` ou "
  + "`oracle[-_]<nom>.py` du dépôt hors dépendances, caches, `vendor`, archives, `fixtures` et `input` — "
  + "lu sur le disque à chaque appel";

//: Les dossiers où un fichier nommé comme un oracle n'est pas un oracle en service.
export const ECARTES = new Set([".git", "node_modules", ".venv", "venv", "__pycache__",
  ".pytest_cache", ".ruff_cache", ".mypy_cache", ".oracles", "Old", "old", "fixtures", "vendor",
  "input"]);

export const EST_UN_ORACLE = (nom) => /^oracle-[\w-]+\.(?:mjs|cjs|js)$/.test(nom) || /^oracle[-_]\w[\w-]*\.py$/.test(nom);
export const EST_UN_GATE = (nom) => /^\w+_gate\.py$/.test(nom);
//: Un point d'entrée ÉCRIT, pas une mention : la ligne commence par `if __name__`.
export const SE_LANCE_SEUL = (source) => /^if\s+__name__\s*==\s*["']__main__["']\s*:/m.test(source);

const PROFONDEUR_MAX = 12;

function parcourir(dossier, trouves, profondeur) {
  if (profondeur > PROFONDEUR_MAX) return;
  let entrees;
  try { entrees = readdirSync(dossier, { withFileTypes: true }); } catch { return; }
  for (const e of entrees) {
    const p = join(dossier, e.name);
    if (e.isDirectory()) { if (!ECARTES.has(e.name)) parcourir(p, trouves, profondeur + 1); }
    else if (e.isFile() && EST_UN_ORACLE(e.name)) trouves.push(p);
  }
}

/** La découverte au contrat commun. `racine` = la racine du dépôt de la forge. */
export function decouvrirOracles(racine) {
  const base = { contrat: CONTRAT, forge: FORGE, racine, regle: REGLE, oracles: [] };
  let estDossier = false;
  try { estDossier = existsSync(racine) && statSync(racine).isDirectory(); } catch { estDossier = false; }
  if (!estDossier) {
    return { ...base, motif: `racine introuvable ou illisible : ${racine} — rien n'a été découvert`, non_juge: [] };
  }
  const chemin = (p) => relative(racine, p).split("\\").join("/");
  const trouves = [];
  const sansEntree = [];
  const gates = join(racine, DOSSIER_GATES);
  let gatesLisibles = true;
  try {
    for (const f of readdirSync(gates).filter(EST_UN_GATE).sort()) {
      let source = "";
      try { source = readFileSync(join(gates, f), "utf8"); } catch { source = ""; }
      if (SE_LANCE_SEUL(source)) trouves.push(join(gates, f)); else sansEntree.push(f.replace(/\.py$/, ""));
    }
  } catch { gatesLisibles = false; }
  parcourir(racine, trouves, 0);
  const oracles = [...new Set(trouves)]
    .map((p) => ({ nom: basename(p, extname(p)), chemin: chemin(p) }))
    .sort((a, b) => (a.chemin < b.chemin ? -1 : a.chemin > b.chemin ? 1 : 0));
  const parNom = new Map();
  for (const o of oracles) parNom.set(o.nom, [...(parNom.get(o.nom) || []), o.chemin]);
  const doublons = [...parNom.entries()].filter(([, c]) => c.length > 1);
  return {
    ...base,
    oracles,
    non_juge: [
      "découvrir n'est pas lancer : cette liste ne dit ni qu'un gate a tourné, ni sur quel projet il s'applique (granularité retenue : la forge, étude du 19/08 §5)",
      ...(gatesLisibles ? [] : [`dossier des gates illisible (${DOSSIER_GATES}) : seule la règle de nom commune a servi`]),
      ...(sansEntree.length
        ? [`${sansEntree.length} gate(s) sans point d'entrée propre (${sansEntree.join(", ")}) : ils jugent sous le nom d'un autre (la CI du template, le superviseur) et ne sont pas découverts — un run ne peut pas consigner un verdict à leur nom`]
        : []),
      ...doublons.map(([nom, chemins]) => `nom porté par ${chemins.length} fichiers (${chemins.join(", ")}) : un verdict qui le nomme ne dit pas lequel a tourné`),
    ],
  };
}

// ---- CLI -------------------------------------------------------------------------------------
const lanceEnDirect = process.argv[1]
  && fileURLToPath(import.meta.url).toLowerCase().split("\\").join("/")
     === resolve(process.argv[1]).toLowerCase().split("\\").join("/");
if (lanceEnDirect) {
  const args = process.argv.slice(2);
  const i = args.indexOf("--racine");
  const racine = resolve(i >= 0 && args[i + 1] ? args[i + 1] : join(dirname(fileURLToPath(import.meta.url)), ".."));
  const r = decouvrirOracles(racine);
  console.log(JSON.stringify(r, null, 1));
  process.exit(r.motif ? 2 : 0);
}
