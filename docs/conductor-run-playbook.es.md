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
- **Regla de merge**: la integración por EPIC es **automática y local** (solo si el doble gate está en verde); el único merge **humano** es hacia GitHub/`main`, **una vez, al final** (HITL 2). Una EPIC bloqueada no se fusiona.
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

**Configuración de partida (enrutamiento onramp).** El «scaffold-first» se generaliza en un *onramp*
elegido por `select_onramp` según la procedencia del proyecto — todos producen el mismo substrate,
por lo que las Fases C→E son idénticas para las tres:
- **From scratch** (`--mode greenfield`) → `ScaffoldOnramp`: genera el esqueleto (esta sección).
- **Continuación** de un proyecto generado por la forge (`--mode brownfield`, repo ya conforme) →
  `NoOnramp`: SIN scaffold; captura una baseline que alimenta la compuerta de no regresión;
  planifica solo los epics nuevos.
- **Proyecto externo** (`--mode brownfield`, repo a normalizar) → `AdapterOnramp` (FastAPI incompleto)
  o `BuilderOnramp` (stack no FastAPI) + HITL-0 si se declara degradación; luego
  `--intent remediation|complement|both`.

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

## Ingesta real (piloto)

La ingesta es heurística por defecto (determinista, sin red). Para activar el **sub-agente
analizador real** (`claude -p`), establece `CONDUCTOR_USE_CLAUDE_ANALYZER=1` (requiere el
CLI `claude` autenticado). El test de integración condicional documenta el camino:
`RUN_CLAUDE_INTEGRATION=1 uv run pytest tests/test_claude_integration.py`.

## Sprint autónomo real (`/bad`, piloto)

El sprint BAD autónomo está **desactivado por defecto**. Para activarlo, establece
`CONDUCTOR_ENABLE_REAL_BAD=1` (requiere `claude` y `gh` autenticados). Postura de seguridad:
la ejecución se apoya en el aislamiento nativo de BAD (un worktree de git por historia),
`AUTO_PR_MERGE=false` está bloqueado por tipo (nunca fusiona automáticamente), y HITL 2 sigue
controlando cada merge. `/bad` se ejecuta con `--dangerously-skip-permissions` y aislamiento
de red relajado — **ejecútalo solo en un repositorio cuya rama `main` esté protegida; nunca
en código cliente sensible sin revisión.** Los resultados se observan mediante `gh pr list`
(la fuente de verdad) y se mapean a los resultados por historia.

## Planificación BMAD real (piloto)

La planificación BMAD se recopila por defecto (`DefaultBmadPlanner` instala BMAD y lee los
artefactos; HITL 1 pausa si está ausente). Para activar la **planificación BMAD autónoma**
mediante `claude -p`, establece `CONDUCTOR_ENABLE_REAL_BMAD=1` (requiere `claude`
autenticado). Solo produce documentos de planificación bajo `_bmad-output/planning-artifacts/`
y siempre está controlada por **HITL 1** antes de cualquier desarrollo — no se cambia código
ni se fusiona nada en esta etapa. Con las tres opciones activadas
(`CONDUCTOR_USE_CLAUDE_ANALYZER`, `CONDUCTOR_ENABLE_REAL_BMAD`, `CONDUCTOR_ENABLE_REAL_BAD`),
la cadena `A→E` completa se ejecuta de verdad, deteniéndose siempre en ambas compuertas HITL.

## Gate de conformidad con el spec real (piloto)

El gate de conformidad con el spec está **desactivado por defecto** (el supervisor solo aplica el
doble gate + la no regresión). Para activar una **revisión de conformidad por story** vía
`claude -p`, definir `CONDUCTOR_ENABLE_SPEC_REVIEW=1` (requiere `claude` autenticado). Compara los
criterios de aceptación de cada story con el diff de su PR: un **under-build** (criterio no
cumplido) bloquea la story (se une a la remediación acotada a 3 reintentos, luego `blocked`); un
**over-build** (comportamiento más allá del spec) es consultivo. Todos los findings se persisten en
`SPEC_FINDINGS.md` con un estado `traité`/`non-traité` para retoma manual posterior. Ningún merge se
ve afectado; HITL 2 no cambia.
