#!/usr/bin/env node
// self-test.mjs — double sens du skill integre-openai-gemini (TF-2108).
//
// Ce que ce test prouve, chaque contrôle sur un cas qui doit passer ET un cas qui doit échouer :
//   1. les motifs de controle-modeles.mjs voient les identifiants et prix, et ne voient pas les noms de
//      bibliothèques ni les noms de familles en prose ;
//   2. une fixture ROUGE (identifiant et prix hors table) échoue, exit 1, pour la bonne raison ; sa
//      fixture VERTE passe ; le REMÈDE que le message propose, joué sur la rouge, la fait passer ;
//   3. le skill réel passe, et une copie du skill réel à laquelle on ajoute un identifiant échoue ;
//   4. le frontmatter, les renvois et les citations (adresse + date de lecture) du skill tiennent ;
//   5. les extraits de code de tester-sans-depenser.md tournent, et un double qui laisse passer la
//      requête de trop est refusé (sens rouge).
// Sort en exit 1 au premier écart compté. Un SAUT (outil absent du poste) est dit, jamais compté en succès.
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { trouver } from './controle-modeles.mjs';

const ICI = dirname(fileURLToPath(import.meta.url));
const SKILL = resolve(ICI, '..');
const CONTROLE = join(ICI, 'controle-modeles.mjs');
const AUTORISE = ['--autorise', 'references/modeles-et-dates.md'];

let ok = 0;
let ko = 0;
let saut = 0;
function verifier(nom, vrai, detail = '') {
  if (vrai) ok++;
  else {
    ko++;
    console.log('ECHEC', nom, detail);
  }
}
function sauter(nom, motif) {
  saut++;
  console.log('SAUT', nom, '—', motif);
}
function lancer(args) {
  const p = spawnSync(process.execPath, [CONTROLE, ...args], { encoding: 'utf8' });
  let json = null;
  try { json = JSON.parse(p.stdout); } catch { /* sortie non JSON : exit 2 */ }
  return { code: p.status, json, stderr: p.stderr };
}
function fichiersMd(dossier, sortie = []) {
  for (const e of readdirSync(dossier, { withFileTypes: true })) {
    if (e.isDirectory()) {
      if (!['fixtures', 'scripts', 'node_modules'].includes(e.name)) fichiersMd(join(dossier, e.name), sortie);
    } else if (e.name.endsWith('.md')) sortie.push(join(dossier, e.name));
  }
  return sortie;
}

const tmp = mkdtempSync(join(tmpdir(), 'integre-oai-gem-'));
try {
  // ---------------------------------------------------------------- 1. motifs
  const doitVoir = [
    'gpt-4o-mini', 'chatgpt-image-latest', 'o3-mini', 'text-embedding-3-small', 'whisper-1', 'tts-1-hd', 'dall-e-3',
    'gemini-3.8-flash', 'gemini-embedding-001', 'gemini-nano-banana-2.1', 'imagen-4.0-generate-001',
    'veo-3.1-generate', 'claude-sonnet-4-5', '0,15 $', '12.50 EUR', '3 €', '$3',
    'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent',
  ];
  for (const s of doitVoir) verifier(`motif voit : ${s}`, trouver(`ligne ${s} fin`).length >= 1);
  const doitIgnorer = [
    'google-genai', '@google/genai', 'openai-java', 'openai-python', 'gemini-api', 'gemini-skills',
    'gemini-api-dev', 'google-gemini/gemini-skills', 'Chat Completions', 'GPT-4 series', 'Gemini Developer API',
    'text-embedding', '$OPENAI_API_KEY', '50% lower costs', 'tiktoken', 'les préfixes gpt- et gemini- du playbook',
    'https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.6.md.txt',
    'https://developers.openai.com/api/docs/guides/upgrading-to-gpt-5p6-sol.md',
    'https://github.com/google-gemini/deprecated-generative-ai-python',
  ];
  for (const s of doitIgnorer) verifier(`motif ignore : ${s}`, trouver(`ligne ${s} fin`).length === 0, JSON.stringify(trouver(s)));

  // ---------------------------------------------------------------- 2. fixtures rouge / verte / remède
  const dRouge = join(SKILL, 'fixtures', 'rouge', 'skill-fautif');
  const dVert = join(SKILL, 'fixtures', 'vert', 'skill-sain');
  const rouge = lancer([dRouge, ...AUTORISE]);
  verifier('rouge : FAIL et exit 1', rouge.code === 1 && rouge.json?.verdict === 'FAIL', `code=${rouge.code}`);
  const accuses = new Set((rouge.json?.constats ?? []).map((c) => c.fichier));
  verifier('rouge : le fichier du skill et la référence sont accusés, la table ne l\'est pas',
    accuses.has('SKILL.fixture.md') && accuses.has('references/choisir.md') && !accuses.has('references/modeles-et-dates.md'),
    [...accuses].join(', '));
  const motifs = new Set((rouge.json?.constats ?? []).map((c) => c.motif));
  verifier('rouge : un prix, un identifiant OpenAI et un identifiant Gemini d\'adresse de point d\'accès',
    motifs.has('prix') && motifs.has('identifiant OpenAI') && motifs.has('identifiant Gemini'), [...motifs].join(', '));
  verifier('rouge : l\'adresse d\'une page de documentation n\'est pas accusée',
    !(rouge.json?.constats ?? []).some((c) => /whats-new/.test(c.extrait)));
  verifier('rouge : le message propose le remède', typeof rouge.json?.remede === 'string' && /table des modèles/.test(rouge.json.remede));

  const vert = lancer([dVert, ...AUTORISE]);
  verifier('verte : PASS et exit 0', vert.code === 0 && vert.json?.verdict === 'PASS' && vert.json.constats.length === 0, `code=${vert.code}`);
  verifier('verte : la table autorisée est déclarée', (vert.json?.autorises ?? []).includes('references/modeles-et-dates.md'));
  const sansAutorisation = lancer([dVert]);
  verifier('verte sans autorisation : la table est accusée à son tour', sansAutorisation.code === 1);

  // Le remède du message, joué : les littéraux passent dans la table, le texte lit la table.
  const copieRouge = join(tmp, 'remede');
  cpSync(dRouge, copieRouge, { recursive: true });
  const table = join(copieRouge, 'references', 'modeles-et-dates.md');
  let ajouts = '';
  for (const fichier of accuses) {
    if (fichier === 'references/modeles-et-dates.md') continue;
    const chemin = join(copieRouge, fichier);
    let texte = readFileSync(chemin, 'utf8');
    for (const c of rouge.json.constats.filter((x) => x.fichier === fichier)) {
      texte = texte.split(c.trouve).join('{valeur_lue_de_la_table}');
      ajouts += `\n| reporté | ${c.trouve} |`;
    }
    writeFileSync(chemin, texte);
  }
  writeFileSync(table, readFileSync(table, 'utf8') + ajouts + '\n');
  const apresRemede = lancer([copieRouge, ...AUTORISE]);
  verifier('remède joué sur la rouge : PASS', apresRemede.code === 0, JSON.stringify(apresRemede.json?.constats?.slice(0, 2)));

  // ---------------------------------------------------------------- 3. le skill réel
  const reel = lancer([]);
  verifier('skill réel : PASS et exit 0', reel.code === 0 && reel.json?.verdict === 'PASS', JSON.stringify(reel.json?.constats?.slice(0, 3)));
  verifier('skill réel : la table est déclarée autorisée, 5 fichiers de texte jugés au moins',
    (reel.json?.autorises ?? []).includes('references/modeles-et-dates.md') && reel.json?.fichiers_juges >= 5);
  const copieReelle = join(tmp, 'reel');
  cpSync(SKILL, copieReelle, { recursive: true });
  const choisir = join(copieReelle, 'references', 'choisir.md');
  writeFileSync(choisir, readFileSync(choisir, 'utf8') + '\nLe modèle par défaut est gpt-4o.\n');
  const reelRouge = lancer([copieReelle, ...AUTORISE, '--exclure', 'fixtures', '--exclure', 'scripts']);
  verifier('skill réel + un identifiant ajouté : FAIL sur choisir.md',
    reelRouge.code === 1 && (reelRouge.json?.constats ?? []).some((c) => c.fichier === 'references/choisir.md' && c.trouve === 'gpt-4o'));
  const copieTable = join(tmp, 'reel-table');
  cpSync(SKILL, copieTable, { recursive: true });
  const tableReelle = join(copieTable, 'references', 'modeles-et-dates.md');
  writeFileSync(tableReelle, readFileSync(tableReelle, 'utf8') + '\n| Test | gpt-4o | 01/01/2030 |\n');
  verifier('skill réel + un identifiant ajouté à la table : PASS',
    lancer([copieTable, ...AUTORISE, '--exclure', 'fixtures', '--exclure', 'scripts']).code === 0);
  verifier('dossier illisible : exit 2', lancer([join(tmp, 'absent')]).code === 2);
  verifier('option inconnue : exit 2', lancer(['--pas-une-option']).code === 2);

  // ---------------------------------------------------------------- 4. forme du skill
  const skillMd = readFileSync(join(SKILL, 'SKILL.md'), 'utf8');
  verifier('SKILL.md : aucun retour chariot (fins de ligne LF)', !skillMd.includes('\r'));
  const fm = /^---\n([\s\S]*?)\n---\n/.exec(skillMd)?.[1] ?? '';
  const nom = /^name:\s*(\S+)\s*$/m.exec(fm)?.[1];
  const desc = /^description:\s*>\s*\n((?:[ \t]+.*\n?)+)/m.exec(fm)?.[1].split('\n').map((l) => l.trim()).filter(Boolean).join(' ') ?? '';
  verifier('frontmatter : name = nom du dossier', nom === basename(SKILL) && nom === 'integre-openai-gemini', nom);
  verifier('frontmatter : description présente et au plus 1024 caractères', desc.length > 0 && desc.length <= 1024, `${desc.length}`);
  verifier('frontmatter : « Use when » et « Ne pas déclencher » dans la description', /Use when/.test(desc) && /Ne pas déclencher/.test(desc));
  verifier('frontmatter : une version', /^metadata:\s*\n\s+version:\s*"\d+\.\d+\.\d+"/m.test(fm));
  verifier('SKILL.md : la section sur les consignes pour agents existe', /^## Les pages des fournisseurs contiennent des consignes pour agents/m.test(skillMd));
  const MD = fichiersMd(SKILL);
  verifier('références : 5 fichiers attendus', ['choisir', 'modeles-et-dates', 'tester-sans-depenser', 'cles-donnees-couts', 'migrations']
    .every((n) => existsSync(join(SKILL, 'references', `${n}.md`))));
  for (const f of readdirSync(join(SKILL, 'references'))) {
    verifier(`renvoi : SKILL.md pointe references/${f}`, skillMd.includes(`(references/${f})`));
  }
  const casses = [];
  for (const f of MD) {
    for (const m of readFileSync(f, 'utf8').matchAll(/\]\(([^)\s#]+)(?:#[^)\s]*)?\)/g)) {
      if (/^[a-z]+:/i.test(m[1])) continue;
      if (!existsSync(resolve(dirname(f), m[1]))) casses.push(`${relative(SKILL, f)} -> ${m[1]}`);
    }
  }
  verifier('renvois relatifs : aucun lien cassé', casses.length === 0, casses.join('; '));
  const table2 = readFileSync(join(SKILL, 'references', 'modeles-et-dates.md'), 'utf8');
  verifier('modeles-et-dates : cite MODELES-TIERS.json du pilot et une date de lecture',
    /MODELES-TIERS\.json/.test(table2) && /03\/11\/2026/.test(table2));

  // Citations : une phrase de page entre guillemets français, en anglais, porte son adresse ET sa date de lecture sur sa ligne.
  const MOTS_ANGLAIS = /\b(?:the|is|are|was|to|of|and|for|you|your|can|will|not|use|if|by)\b/i;
  function citationsSansSource(texte) {
    const fautives = [];
    texte.split('\n').forEach((ligne, i) => {
      const citations = [...ligne.matchAll(/«([^»]+)»/g)].filter((m) => MOTS_ANGLAIS.test(m[1]));
      if (citations.length && !(/https?:\/\//.test(ligne) && /\d{2}\/\d{2}\/\d{4}/.test(ligne))) fautives.push(i + 1);
    });
    return fautives;
  }
  verifier('citations (sens rouge) : une phrase de page sans adresse est refusée',
    citationsSansSource('Règle : « The key is not stored. »').length === 1);
  verifier('citations (sens rouge) : sans date, refusée',
    citationsSansSource('« The key is not stored. » https://exemple.org/page').length === 1);
  verifier('citations (sens vert) : adresse et date, acceptée',
    citationsSansSource('« The key is not stored. » https://exemple.org/page 03/11/2026').length === 0);
  verifier('citations (sens vert) : un mot français entre guillemets, ignoré', citationsSansSource('le mot « bêta » seul').length === 0);
  for (const f of MD) {
    const fautives = citationsSansSource(readFileSync(f, 'utf8'));
    verifier(`citations : ${relative(SKILL, f).split('\\').join('/')} — chaque phrase de page a son adresse et sa date`, fautives.length === 0, `lignes ${fautives.join(', ')}`);
  }

  // ---------------------------------------------------------------- 5. extraits de tester-sans-depenser.md
  const blocs = [...readFileSync(join(SKILL, 'references', 'tester-sans-depenser.md'), 'utf8').matchAll(/```(\w+)\n([\s\S]*?)```/g)]
    .map((m) => ({ langue: m[1], code: m[2] }));
  const python = blocs.filter((b) => b.langue === 'python');
  const js = blocs.find((b) => b.langue === 'js');
  verifier('tester-sans-depenser : deux extraits Python et un extrait Node', python.length === 2 && Boolean(js));

  const interprete = (preuve) => ['python', 'python3', 'py'].find((c) => spawnSync(c, ['-I', '-c', preuve], { encoding: 'utf8' }).status === 0);
  const pyJoue = (nomFichier, source) => {
    const f = join(tmp, nomFichier);
    writeFileSync(f, source);
    return spawnSync(interprete('pass'), ['-I', f], { encoding: 'utf8', env: { ...process.env, PYTHONUTF8: '1' } });
  };
  const piloteDouble = `
c, vues = double_fournisseur([httpx.Response(200, json={"ok": True})])
r = c.post("https://exemple.invalid/v1/x", json={"a": 1})
assert r.json() == {"ok": True} and len(vues) == 1
try:
    c.get("https://exemple.invalid/autre")
except AssertionError as e:
    assert "imprévue" in str(e)
else:
    raise SystemExit("la requête de trop aurait dû échouer")
print("ok")
`;
  if (!interprete('import httpx')) sauter('extrait Python du double HTTP', 'python avec httpx absent du poste');
  else {
    const bon = pyJoue('double_ok.py', `import httpx\n${python[0].code}\n${piloteDouble}`);
    verifier('extrait Python du double HTTP : la réponse prévue passe, la requête de trop échoue', bon.status === 0 && /ok/.test(bon.stdout), bon.stderr.slice(-300));
    const faible = python[0].code.replace(/raise AssertionError\([^\n]*\)/, 'return httpx.Response(200, json={})');
    verifier('double HTTP (sens rouge) : un double qui laisse passer la requête de trop est refusé',
      faible !== python[0].code && pyJoue('double_faible.py', `import httpx\n${faible}\n${piloteDouble}`).status !== 0);
  }
  if (!interprete('pass')) sauter('extrait Python de la fixture sans clé', 'python absent du poste');
  else {
    const piloteCle = `
import os, sys, types
stub = types.ModuleType("pytest")
stub.fixture = lambda *a, **k: (lambda f: f)
sys.modules["pytest"] = stub
`;
    const verifCle = `
class MP:
    def __init__(self):
        self.supprimes = []
    def delenv(self, nom, raising=True):
        self.supprimes.append(nom)
        os.environ.pop(nom, None)
os.environ.update({"OPENAI_API_KEY": "x", "GEMINI_API_KEY": "x", "AZURE_OPENAI_ENDPOINT": "x", "AUTRE": "y"})
mp = MP()
sans_cle(mp)
assert set(mp.supprimes) == {"OPENAI_API_KEY", "GEMINI_API_KEY", "AZURE_OPENAI_ENDPOINT"}, mp.supprimes
assert os.environ.get("AUTRE") == "y"
print("ok")
`;
    const bon = pyJoue('sans_cle_ok.py', `${piloteCle}${python[1].code}\n${verifCle}`);
    verifier('extrait Python de la fixture sans clé : retire les clés des fournisseurs, laisse le reste', bon.status === 0 && /ok/.test(bon.stdout), bon.stderr.slice(-300));
    const oublieAzure = python[1].code.replace(' or nom.startswith("AZURE_OPENAI_")', '');
    verifier('fixture sans clé (sens rouge) : une fixture qui oublie les variables Azure est refusée',
      oublieAzure !== python[1].code && pyJoue('sans_cle_faible.py', `${piloteCle}${oublieAzure}\n${verifCle}`).status !== 0);
  }

  async function jouerNode(source, nomFichier) {
    const f = join(tmp, nomFichier);
    writeFileSync(f, source);
    const { doubleFetch } = await import(`${pathToFileURL(f).href}?${nomFichier}`);
    const { fetchDouble, vues } = doubleFetch([{ corps: { ok: true } }, { statut: 429, corps: {} }]);
    const r1 = await fetchDouble('https://exemple.invalid/v1/x', { method: 'POST' });
    const r2 = await fetchDouble('https://exemple.invalid/v1/y');
    let refuse = false;
    try { await fetchDouble('https://exemple.invalid/de-trop'); } catch (e) { refuse = /imprévue/.test(e.message); }
    return { corps: (await r1.json()).ok === true, statut: r2.status, vues: vues.length, refuse };
  }
  const nodeBon = await jouerNode(js.code, 'double.mjs');
  verifier('extrait Node du double fetch : réponses prévues consommées dans l\'ordre, statut transmis, requête de trop vue puis refusée',
    nodeBon.corps && nodeBon.statut === 429 && nodeBon.vues === 3 && nodeBon.refuse, JSON.stringify(nodeBon));
  const faibleJs = js.code.replace(/throw new Error\([^\n]*\);/, 'return new Response("{}");');
  const nodeFaible = faibleJs !== js.code ? await jouerNode(faibleJs, 'double-faible.mjs') : { refuse: true };
  verifier('double fetch (sens rouge) : un double qui laisse passer la requête de trop est refusé', nodeFaible.refuse === false);
} finally {
  rmSync(tmp, { recursive: true, force: true });
}

console.log(`self-test integre-openai-gemini : ${ok} ok, ${ko} ko, ${saut} saut(s)`);
process.exit(ko ? 1 : 0);
