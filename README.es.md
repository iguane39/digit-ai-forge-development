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

**Epic 0 (Bootstrap) — entregado y verificado.** Esqueleto `conductor/` tipado, contratos del
pipeline `A→E`, CI de doble compuerta, vendorizado de BAD `@v1.2.0`, semilla de dogfooding. La
compuerta de código está verde en GitHub Actions. Siguiente: Epic 1 (scaffold-first), Epic 2
(eje de diseño), Epic 3 (bucle completo) — ver [`docs/plan-implementation.md`](docs/plan-implementation.md).

## Licencia

[MIT](LICENSE) © 2026 Digit-AI.

---
*Digit-AI · Consultoría y estrategia de IA · acelerador SaaS · 2026*
