#!/usr/bin/env node
// controle-modeles.mjs — aucun identifiant de modèle ni prix hors de la table qui les porte (TF-2108).
//
// POURQUOI. Un identifiant de modèle écrit dans le code d'un produit ou dans un skill est périmé à la
// date où le fournisseur l'arrête ; un prix l'est plus vite encore. La règle de la forge
// (docs/run-playbook.md, « Données volatiles en base ») les range dans une table éditable, datée et
// sourcée. Ce contrôle la rend exécutable pour les familles d'identifiants d'OpenAI, de Gemini et de
// Claude, là où le grep du playbook ne couvre que trois préfixes.
//
// USAGE
//   node controle-modeles.mjs                       le skill lui-même : tout est jugé sauf
//                                                   references/modeles-et-dates.md, fixtures/ et scripts/
//   node controle-modeles.mjs <dossier> [--autorise <chemin>]... [--exclure <dossier>]...
//                                                   un dossier de produit ; --autorise nomme un fichier
//                                                   (chemin relatif, séparateur /) qui peut porter des
//                                                   identifiants, par exemple la migration de peuplement
// SORTIE  JSON sur stdout : { controle, verdict, racine, fichiers_juges, constats[], autorises[], non_juge[] }
// EXIT    0 PASS · 1 FAIL (au moins un constat) · 2 racine ou option illisible. Jamais d'exit 0 sur FAIL.
//
// LIMITES (aussi dites au non_juge) : les noms de familles écrits en prose avec majuscules (par exemple
// ceux que les pages des fournisseurs emploient dans leurs titres) ne sont pas des identifiants et ne
// sont pas jugés ; un identifiant construit par concaténation n'est pas vu ; les fichiers .env* ne sont
// jamais ouverts ; l'adresse d'une page de documentation ou d'un dépôt de bibliothèque est écartée avant
// jugement (son chemin porte parfois le nom d'un modèle), celle d'un point d'accès de l'API ne l'est pas.
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

export const NOM = 'controle-modeles';

// Motifs sensibles à la casse : un identifiant d'API s'écrit en minuscules ; « GPT-4 series » dans une
// phrase est un nom de famille, pas un identifiant.
export const MOTIFS = [
  { nom: 'identifiant OpenAI', re: /\b(?:gpt|chatgpt)-[a-z0-9][\w.-]*/g },
  { nom: 'identifiant OpenAI (raisonnement)', re: /\bo[1-9]-(?:mini|pro|preview|deep-research)\b/g },
  { nom: 'identifiant de plongement', re: /\btext-embedding-[a-z0-9][\w.-]*/g },
  { nom: 'identifiant OpenAI (audio, image)', re: /\b(?:whisper-\d|tts-1(?:-hd)?\b|dall-e-\d)[\w.-]*/g },
  { nom: 'identifiant Gemini', re: /\bgemini-(?:\d|nano|omni|embedding|robotics|live|flash|pro|exp)[\w.-]*/g },
  { nom: 'identifiant Google (image, vidéo, musique)', re: /\b(?:imagen|veo|lyria)-\d[\w.-]*/g },
  { nom: 'identifiant Claude', re: /\bclaude-(?:opus|sonnet|haiku|\d)[\w.-]*/g },
  { nom: 'prix', re: /[$€]\s?\d|\d(?:[.,]\d+)?\s?(?:€|\$|USD|EUR)(?![\w])/g },
];

// Une adresse de PAGE de documentation (ou de dépôt de bibliothèque) porte parfois le nom d'un modèle dans
// son chemin : c'est une adresse que le skill cite, pas un identifiant qu'un code emploie. On l'écarte avant
// de juger la ligne. Une adresse de POINT D'ACCÈS (api.openai.com, generativelanguage.googleapis.com,
// *.openai.azure.com) n'est pas écartée : un identifiant qui s'y trouve est un identifiant en dur.
export const ADRESSE_DOC = /https?:\/\/(?:developers\.openai\.com|platform\.openai\.com|openai\.com|ai\.google\.dev|aistudio\.google\.com|cloud\.google\.com|learn\.microsoft\.com|github\.com|pub\.dev|pkg\.go\.dev|www\.npmjs\.com|pypi\.org)\/[^\s)>\]|`'"]*/g;

const EXTENSIONS = new Set(['.md', '.txt', '.py', '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.json',
  '.jsonl', '.yml', '.yaml', '.toml', '.sql', '.sh', '.ps1', '.html', '.ini', '.cfg']);
const DOSSIERS_ECARTES = new Set(['.git', 'node_modules', '.venv', 'venv', '__pycache__', 'dist', 'build',
  '.next', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.oracles']);
const TAILLE_MAX = 2 * 1024 * 1024;

export const REMEDE = 'écrire l\'identifiant ou le prix dans la table des modèles du produit (pour ce skill : '
  + 'references/modeles-et-dates.md), avec sa date de relevé et son adresse, puis lire le rôle par la table, '
  + 'jamais le littéral';

/** Constats d'un texte : une entrée par occurrence, avec son numéro de ligne (1 = première). */
export function trouver(texte) {
  const constats = [];
  texte.split(/\r?\n/).forEach((ligne, i) => {
    const nette = ligne.replace(ADRESSE_DOC, ' ');
    for (const { nom, re } of MOTIFS) {
      re.lastIndex = 0;
      for (const m of nette.matchAll(re)) {
        // Un point ou un tiret final est la ponctuation de la phrase, pas la fin de l'identifiant.
        constats.push({ ligne: i + 1, motif: nom, trouve: m[0].trim().replace(/[.-]+$/, ''), extrait: ligne.trim().slice(0, 140) });
      }
    }
  });
  return constats;
}

function parcourir(racine, exclure) {
  const fichiers = [];
  const non_juge = [];
  const pile = [racine];
  while (pile.length) {
    const dossier = pile.pop();
    for (const e of readdirSync(dossier, { withFileTypes: true })) {
      const chemin = join(dossier, e.name);
      if (e.isDirectory()) {
        if (!DOSSIERS_ECARTES.has(e.name) && !exclure.has(e.name)) pile.push(chemin);
        continue;
      }
      if (!e.isFile()) continue;
      // Un .env ne s'ouvre jamais ; seul l'exemple (.env.example) porte des noms, pas des valeurs.
      if (e.name.startsWith('.env') && e.name !== '.env.example') {
        non_juge.push(`${relatif(racine, chemin)} : fichier .env, jamais ouvert`);
        continue;
      }
      const ext = e.name === '.env.example' ? '.txt' : e.name.slice(e.name.lastIndexOf('.'));
      if (!EXTENSIONS.has(ext)) continue;
      if (statSync(chemin).size > TAILLE_MAX) {
        non_juge.push(`${relatif(racine, chemin)} : plus de 2 Mo, non lu`);
        continue;
      }
      fichiers.push(chemin);
    }
  }
  return { fichiers: fichiers.sort(), non_juge };
}

const relatif = (racine, chemin) => relative(racine, chemin).split(sep).join('/');

/** Juge un dossier. `autorise` : chemins relatifs (séparateur /) qui peuvent porter des identifiants. */
export function juger(racine, { autorise = [], exclure = [] } = {}) {
  const { fichiers, non_juge } = parcourir(racine, new Set(exclure));
  const exemptes = new Set(autorise);
  const constats = [];
  const autorises = [];
  for (const f of fichiers) {
    const rel = relatif(racine, f);
    if (exemptes.has(rel)) {
      autorises.push(rel);
      continue;
    }
    for (const c of trouver(readFileSync(f, 'utf8'))) constats.push({ fichier: rel, ...c });
  }
  return {
    controle: NOM,
    verdict: constats.length ? 'FAIL' : 'PASS',
    racine,
    fichiers_juges: fichiers.length - autorises.length,
    constats,
    autorises,
    remede: constats.length ? REMEDE : null,
    non_juge: [
      ...non_juge,
      'noms de familles écrits avec majuscules en prose (non jugés : ce ne sont pas des identifiants d\'API)',
      'identifiants construits par concaténation ou lus d\'une variable',
      'adresses de pages de documentation et de dépôts de bibliothèques (écartées avant le jugement ; une adresse de point d\'accès reste jugée)',
    ],
  };
}

function lireArguments(argv) {
  const opts = { dossier: null, autorise: [], exclure: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--autorise' || a === '--exclure') {
      if (i + 1 >= argv.length) throw new Error(`${a} attend une valeur`);
      opts[a.slice(2)].push(argv[++i].split('\\').join('/'));
    } else if (a.startsWith('--')) throw new Error(`option inconnue : ${a}`);
    else if (opts.dossier === null) opts.dossier = a;
    else throw new Error(`argument en trop : ${a}`);
  }
  return opts;
}

function principal() {
  let opts;
  try {
    opts = lireArguments(process.argv.slice(2));
  } catch (e) {
    console.error(`${NOM} : ${e.message}`);
    return 2;
  }
  let racine;
  if (opts.dossier === null) {
    racine = resolve(dirname(fileURLToPath(import.meta.url)), '..');
    opts.autorise.push('references/modeles-et-dates.md');
    opts.exclure.push('fixtures', 'scripts');
  } else racine = resolve(opts.dossier);
  if (!existsSync(racine) || !statSync(racine).isDirectory()) {
    console.error(`${NOM} : dossier illisible : ${racine}`);
    return 2;
  }
  const verdict = juger(racine, opts);
  console.log(JSON.stringify(verdict, null, 2));
  return verdict.verdict === 'PASS' ? 0 : 1;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = principal();
}
