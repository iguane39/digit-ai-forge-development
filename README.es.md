# Digit-AI SaaS Forge

[English](README.md) · [Français](README.fr.md) · **Español** · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português](README.pt.md)

> **De la idea a un SaaS listo para producción, en un solo comando — bajo una doble compuerta de código y diseño.**

Digit-AI SaaS Forge es un acelerador de SaaS agéntico. Una **capa de orquestación ligera**
(`conductor/`) secuencia y restringe motores de terceros probados para llevar una intención
de producto hasta un repositorio SaaS estructurado, probado y conforme a una guía de marca —
sin reescribir ni bifurcar nunca esos motores.

La forge no reinventa la planificación, el andamiaje, el desarrollo autónomo ni el linting de
diseño. Los **orquesta**.

## Cómo funciona — una cadena de 5 etapas

| Etapa | Nombre | Función |
|-------|--------|---------|
| **A** | Encuadre | Convertir una idea + restricciones en una config de misión (objetivo, alcance SaaS, marca) |
| **B** | Scaffold-first | Generar el esqueleto de producción **antes de cualquier agente** |
| **C** | Puente BMAD | Lanzar la planificación ágil → PRD, arquitectura, épicas, historias — *compuerta HITL 1* |
| **D** | Adaptador de sprint | Colocar el backlog donde el motor autónomo lo espera |
| **E** | Supervisor | Ejecutar el sprint autónomo bajo la doble compuerta — *compuerta HITL 2* |

Dos principios estructurales:

- **Scaffold-first** — el esqueleto de producción existe antes de que los agentes escriban una
  línea de código.
- **Doble compuerta** — ninguna historia se fusiona si no pasan **ambos**: la CI de código
  (ruff, mypy, pytest, Playwright) **y** el lint de diseño (WCAG 2.2 AA, referencias rotas,
  on-system).

Dos puntos de validación humana (HITL): aprobación del PRD y la arquitectura, luego revisión
y merge final. La fusión automática está deshabilitada por diseño.

## Motores orquestados (fijados y vendorizados, nunca bifurcados)

| Motor | Capa |
|-------|------|
| [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | Planificación ágil (brief → PRD → historias) |
| [bmad-autonomous-development](https://github.com/stephenleo/bmad-autonomous-development) | Ejecución autónoma del sprint (un worktree git por historia) |
| [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | Objetivo de producción determinista (FastAPI + React + PostgreSQL) |
| [@google/design.md](https://github.com/google-labs-code/design.md) | Lint del sistema de diseño (la compuerta de diseño) |

## Estructura del repositorio

| Ruta | Contenido |
|------|-----------|
| [`digitai-saas-forge/`](digitai-saas-forge/) | El código: `conductor/` (framework maestro), objetivo parametrizable, compuertas, CI |
| [`docs/`](docs/) | Corpus de diseño: análisis, PRD (formato BMAD), arquitectura, plan de implementación, notas de spike, decisiones de ejecución |
| [`input/`](input/) | El dosier fundacional original |

## Inicio rápido

```bash
cd digitai-saas-forge
uv sync
uv run pytest        # compuerta de código (ruff + mypy strict + pytest)
conductor --version
```

## Estado

- **Epic 0 — Bootstrap** ✅ fusionado. Esqueleto `conductor/` tipado, contratos `A→E`, CI de doble compuerta, vendorizado de BAD `@v1.2.0`, semilla de dogfooding.
- **Epic 1 — Scaffold-first** ✅ fusionado. Encuadre (A) + scaffold (B) + catálogo de 11 bricks + compuerta de código.
- **Epic 2 — Eje de diseño** ✅ fusionado. Compuerta de diseño bloqueante (`@google/design.md@0.3.0` + política de severidad), `DESIGN.md`, estilo vendorizado, exportación de tokens.
- **Epic 3 — Bucle completo** ✅ fusionado. Puente BMAD (C) + HITL 1, adaptador de sprint (D), supervisor (E) que invoca `/bad` con compuerta de diseño por historia, remediación de 3 reintentos y HITL 2 — fusión automática bloqueada.

Los cuatro epics están integrados; ambas compuertas están verdes en GitHub Actions. La cadena `A→E` está cableada y probada; la ejecución real de BMAD/`/bad` requiere un harness de Claude Code. Ver [`docs/plan-implementation.md`](docs/plan-implementation.md).

## Lanzar un build — metodología

La ejecución está orquestada pero **gobernada**: se detiene en dos puntos de validación humana
por diseño y nunca fusiona automáticamente. Se adjunta un dosier de especificaciones/restricciones;
el operador separa el alcance de las restricciones y luego recorre la cadena:

1. **Clasificar** los adjuntos — alcance (el *qué*) vs restricciones (el *cómo*).
2. **Preflight** — `gh` auth + token, `uv`/`node`, red, clonar la forge.
3. **Encuadre (A)** — derivar un `MissionConfig` (11 bricks build/buy, t0 forzadas), luego validar.
4. **Scaffold-first (B)** — generar el esqueleto antes de cualquier agente.
5. **Planificación BMAD (C) → HITL 1** — PRD/arquitectura/épicas; aprobación humana requerida.
6. **Config de sprint (D)** — layout del backlog + sección `bad:` (`auto_pr_merge=false`).
7. **Sprint supervisado (E) → HITL 2** — `/bad` por historia, doble compuerta, 3 reintentos; ningún merge sin revisión humana.

Prompt de operador completo: **[`docs/conductor-run-playbook.md`](docs/conductor-run-playbook.md)**.

## Licencia

[MIT](LICENSE) © 2026 Digit-AI.

---
*Digit-AI · Consultoría y estrategia de IA · acelerador SaaS · 2026*
