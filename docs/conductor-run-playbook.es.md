# Conductor Run — Playbook del operador

> 🌍 [English](conductor-run-playbook.md) · [Français](conductor-run-playbook.fr.md) · [Español](conductor-run-playbook.es.md) · [Deutsch](conductor-run-playbook.de.md) · [Italiano](conductor-run-playbook.it.md) · [Português](conductor-run-playbook.pt.md)

Este playbook es el prompt del operador para dirigir un `conductor run` de extremo a extremo
de la Digit-AI SaaS Forge **desde otro proyecto Claude Code**, adjuntando un dosier de
especificaciones/restricciones. La ejecución está orquestada pero **gobernada**: se detiene en
dos puntos de validación humana (HITL) por diseño y nunca fusiona automáticamente.

## La metodología en una pantalla

```
adjuntos ─▶ [−1] clasificar (alcance vs restricciones)
        ─▶ [0]  preflight (gh/token, uv/node, red, clonar forge)
        ─▶ [A]  encuadre → MissionConfig (11 bricks build/buy, t0 forzadas)   ⟲ validar
        ─▶ [B]  scaffold-first (copier + bricks, ANTES de cualquier agente)
        ─▶ [C]  planificación BMAD (epics.md)                                 ⛔ HITL 1
        ─▶ [D]  config de sprint (sprint-status.yaml + bad:, auto_pr_merge=false)
        ─▶ [E]  sprint /bad + doble compuerta (código + diseño) + 3 reintentos ⛔ HITL 2
                → Pull Requests PR-ready (nunca fusionadas automáticamente)
```

Barreras innegociables: **scaffold-first**, **doble compuerta** (CI de código + lint de diseño),
**2 HITL**, **dependencias fijadas/vendorizadas** (BAD `@v1.2.0`, `@google/design.md@0.3.0`),
**`auto_pr_merge=false`**.

## El prompt del operador (pega esto en el otro proyecto Claude Code)

```markdown
# Misión — Dirigir un `conductor run` (Digit-AI SaaS Forge) de la idea al PR-ready

Eres el operador de la `digit-ai-saas-forge` en ESTE proyecto. Llevarás un alcance de producto
hasta Pull Requests PR-ready, orquestando la cadena A→E del conductor. NO tienes permiso para
saltarte sus barreras.

## Entradas (proporcionadas como ADJUNTOS)
Uno o varios archivos están adjuntos (specs, restricciones, notas técnicas — formatos diversos:
md, pdf, docx, txt, imágenes). NO están preordenados.

Repo de la forge: https://github.com/iguane39/digit-ai-saas-forge
Repo destino de las PR (donde se genera el SaaS): {{ org/repo, o "a crear" }}

## Fase −1 — Analizar y clasificar los adjuntos
Lee CADA adjunto por completo, luego separa el contenido en dos categorías — sin inventar nada,
sin perder nada:
- **ALCANCE (el "qué")**: intención de producto, usuarios/personas, funcionalidades, user
  stories, reglas de negocio, pantallas/flujos, datos, criterios de éxito de producto.
- **RESTRICCIONES (el "cómo / en qué marco")**: stack impuesta, integraciones, seguridad/
  cumplimiento (RGPD, multi-tenancy, RBAC, SSO…), rendimiento, hosting, presupuesto, plazo,
  carta/marca y diseño, requisitos de tests/CI, dependencias permitidas.
Reglas: un requisito ambiguo → ponlo en ambas y márcalo "a arbitrar"; algo que no es ninguna →
lístalo como "fuera de marco / ignorar"; si los archivos se contradicen → reporta el conflicto
(no decidas solo).
→ Produce una TABLA DE CLASIFICACIÓN (Archivo · Extracto · Categoría · Nota) y ESPERA mi
validación del orden antes del preflight. Es la base de todo lo demás.

## Barreras (INNEGOCIABLES)
- **Scaffold-first**: el esqueleto de producción existe antes de cualquier agente (B antes de C).
- **Doble compuerta**: ninguna historia se entrega si la CI de código O el lint de diseño falla.
- **2 HITL**: (1) tras la planificación BMAD, (2) antes de cualquier merge. En CADA HITL te
  DETIENES, presentas un resumen de decisión y ESPERAS mi aprobación explícita. Estas paradas
  son intencionadas — no son fallos.
- **`auto_pr_merge=false`**: NUNCA auto-fusionas. No te auto-apruebas ningún HITL.
- **Dependencias fijadas/vendorizadas**: BAD `@v1.2.0`, `@google/design.md@0.3.0`.
- "De extremo a extremo" = orquestado sin paso manual FUERA de los 2 HITL previstos.

## Fase 0 — Preflight (fail-fast: si algo falla, DETENTE y dilo)
1. `gh auth status` OK y `GITHUB_PERSONAL_ACCESS_TOKEN` exportado (`export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)`).
2. `uv`, `node`/`npx`, `git`, acceso a red (npx/copier/bmad) disponibles.
3. Forge accesible: clónala y `uv sync` en `digitai-saas-forge/`.
4. Confirma el repo destino de las PR y la carpeta destino del SaaS generado.
→ Devuelve una tabla "preflight OK/KO" antes de continuar.

## Fase A — Encuadre (el mapeo = el trabajo real)
Desde el ALCANCE + RESTRICCIONES validados en la Fase −1, PROPÓN un `MissionConfig` explícito:
- `idea`: una frase de síntesis (NO los adjuntos completos).
- `target`: objetivo (por defecto `fastapi-saas`).
- `saas_scope`: para CADA uno de los 11 bricks, una decisión `build`/`buy`/`skip` JUSTIFICADA
  por los adjuntos. Nota: `multi-tenancy`, `rbac`, `auth-sso` están FORZADAS a `build` (t0).
- `brand_charter` + `style_slug`: si no se adjunta carta, dilo y propón el `DESIGN.md` por
  defecto (el lint de diseño corre sobre él) — a validar.
- `budget`/`deadline` y `max_parallel_stories` (limítalo, por defecto 2-3) para acotar el coste.
- Lista los requisitos de alcance que NO supiste mapear (zona gris).
→ PRESENTA este `MissionConfig` y ESPERA mi validación antes de la Fase B (encuadre = checkpoint).

## Fase B — Scaffold-first
Genera el esqueleto vía `copier` + injerta los bricks elegidos (t0 incluidos). Verifica que el
harness CI (compuerta de código) esté en su sitio. NO invoques ningún agente antes de terminar B.

## Fase C — Puente BMAD → HITL 1
`npx bmad-method install --modules bmm,tea`, luego produce la planificación en
`_bmad-output/planning-artifacts/epics.md` (PRD, arquitectura, épicas, historias).
→ **HITL 1**: presenta un resumen PRD + arquitectura + épicas/historias. DETENTE. Escribe la
config de sprint solo tras mi "go".

## Fase D — Adaptador de sprint
Escribe `_bmad-output/implementation-artifacts/sprint-status.yaml` y la sección `bad:` de
`_bmad/config.yaml` con **`auto_pr_merge: false`**, `max_parallel_stories` limitado, tiers de
modelos. NO compiles un grafo (BAD lo construye él mismo).

## Fase E — Supervisor (sprint bajo la doble compuerta)
Invoca el skill `/bad` (1 worktree/historia, pipeline de 7 pasos, compuerta de código interna)
con `AUTO_PR_MERGE=false`. Para cada historia:
- Compuerta de diseño: `npx --yes -p @google/design.md@0.3.0 designmd lint --format json` LUEGO
  aplica la política de severidad (NO confíes en el exit code: un fallo WCAG puede salir como
  `warning` → exit 0). Bloquea en contraste/refs/secciones faltantes incluso en `warning`.
- Si una compuerta falla: hasta **3 reintentos** del agente, si no marca la historia `blocked`
  + escala.
→ **HITL 2**: presenta las PR PR-ready (checklist: PR abierta y sin fusionar, doble compuerta
verde, cuerpo generado, issue vinculada, mergeable=clean, asignada a revisión) y las historias
`blocked`. DETENTE. NO FUSIONES NADA.

## Salida esperada y registro
- Un REGISTRO DE EJECUCIÓN: clasificación de adjuntos, estado por fase, decisiones de encuadre,
  historias ready vs blocked, enlaces de PR, coste/tiempo aproximados, zonas grises.
- Recuerda dónde vive el SaaS generado y cómo REANUDAR tras cada HITL.
- Si el alcance es grande: propón primero un slice MVP / primera épica, hazlo validar, luego
  extiende — en lugar de lanzar todo el sprint de golpe.

## Prohibido (cierra las puertas)
- No proceses adjuntos sin leerlos y clasificarlos (Fase −1). No pegues un documento entero como
  `idea`. No te saltes el preflight. No fuerces `auto_pr_merge=true`. No te auto-apruebes ningún
  HITL. No ignores ninguna restricción sin marcarla en zona gris. No bifurques
  BMAD/BAD/el template/design.md.
```
