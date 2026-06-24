# Digit-AI SaaS Forge

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · **Português**

> **Da ideia a um SaaS pronto para produção, em um único comando — sob um duplo gate de código e design.**

Digit-AI SaaS Forge é um acelerador de SaaS agêntico. Uma **camada de orquestração enxuta**
(`conductor/`) sequencia e restringe motores de terceiros consolidados para levar uma intenção
de produto até um repositório SaaS estruturado, testado e em conformidade com uma identidade
de marca — sem nunca reescrever nem fazer fork desses motores.

A forge não reinventa o planejamento, o scaffolding, o desenvolvimento autônomo nem o linting
de design. Ela os **orquestra**.

## Como funciona — uma cadeia de 5 etapas

> 📊 **Visão geral:** [diagrama interativo do processo — 6 idiomas](docs/forge-process-schema.html?lang=pt) (entradas · A→E · gates · HITL · ciclo iterativo).

| Etapa | Nome | Função |
|-------|------|--------|
| **A** | Enquadramento | Transformar uma ideia + restrições em uma config de missão (alvo, escopo SaaS, marca) |
| **B** | Scaffold-first | Gerar o esqueleto de produção **antes de qualquer agente** |
| **C** | Ponte BMAD | Iniciar o planejamento ágil → PRD, arquitetura, épicos, histórias — *gate HITL 1* |
| **D** | Adaptador de sprint | Colocar o backlog onde o motor autônomo o espera |
| **E** | Supervisor | Executar o sprint autônomo sob o duplo gate — *gate HITL 2* |

Dois princípios estruturais:

- **Scaffold-first** — o esqueleto de produção existe antes que os agentes escrevam uma linha
  de código.
- **Duplo gate** — nenhuma história é mesclada se não passarem **ambos**: a CI de código
  (ruff, mypy, pytest, Playwright) **e** o lint de design (WCAG 2.2 AA, referências quebradas,
  on-system).

Dois pontos de validação humana (HITL): aprovação do PRD e da arquitetura, depois revisão e
merge final. O merge automático está desativado por concepção.

## Motores orquestrados (fixados e vendorizados, nunca forkados)

| Motor | Camada |
|-------|--------|
| [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | Planejamento ágil (brief → PRD → histórias) |
| [bmad-autonomous-development](https://github.com/stephenleo/bmad-autonomous-development) | Execução autônoma do sprint (um worktree git por história) |
| [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | Alvo de produção determinístico (FastAPI + React + PostgreSQL) |
| [@google/design.md](https://github.com/google-labs-code/design.md) | Lint do design system (o gate de design) |

## Estrutura do repositório

| Caminho | Conteúdo |
|---------|----------|
| [`digitai-saas-forge/`](digitai-saas-forge/) | O código: `conductor/` (framework mestre), alvo parametrizável, gates, CI |
| [`docs/`](docs/) | Corpus de design: análise, PRD (formato BMAD), arquitetura, plano de implementação, notas de spike, decisões de execução |
| [`input/`](input/) | O dossiê fundador original |

## Início rápido

```bash
cd digitai-saas-forge
uv sync
uv run pytest        # gate de código (ruff + mypy strict + pytest)
conductor --version
```

## Estado

- **Epic 0 — Bootstrap** ✅ integrado. Esqueleto `conductor/` tipado, contratos `A→E`, CI de duplo gate, vendoring de BAD `@v1.2.0`, seed de dogfooding.
- **Epic 1 — Scaffold-first** ✅ integrado. Enquadramento (A) + scaffold (B) + catálogo de 11 bricks + gate de código.
- **Epic 2 — Eixo de design** ✅ integrado. Gate de design bloqueante (`@google/design.md@0.3.0` + política de severidade), `DESIGN.md`, estilo vendorizado, exportação de tokens.
- **Epic 3 — Laço completo** ✅ integrado. Ponte BMAD (C) + HITL 1, adaptador de sprint (D), supervisor (E) que invoca `/bad` com gate de design por história, remediação de 3 retries e HITL 2 — merge automático bloqueado.

Os quatro epics estão integrados; ambos os gates estão verdes no GitHub Actions. A cadeia `A→E` está conectada e testada; a execução real de BMAD/`/bad` requer um harness Claude Code. Ver [`docs/plan-implementation.md`](docs/plan-implementation.md).

## Iniciar um build — metodologia

A execução é orquestrada mas **governada**: ela para em dois checkpoints humanos por concepção
e nunca faz merge automático. Anexa-se um dossiê de especificações/restrições; o operador separa
o escopo das restrições e percorre a cadeia:

1. **Classificar** os anexos — escopo (o *quê*) vs restrições (o *como*).
2. **Preflight** — `gh` auth + token, `uv`/`node`, rede, clonar a forge.
3. **Enquadramento (A)** — derivar um `MissionConfig` (11 bricks build/buy, t0 forçadas), depois validar.
4. **Scaffold-first (B)** — gerar o esqueleto antes de qualquer agente.
5. **Planejamento BMAD (C) → HITL 1** — PRD/arquitetura/épicos; aprovação humana exigida.
6. **Config de sprint (D)** — layout do backlog + seção `bad:` (`auto_pr_merge=false`).
7. **Sprint supervisionado (E) → HITL 2** — `/bad` por história, duplo gate, 3 retries; nenhum merge sem revisão humana.

**Comece aqui — ponto de entrada único:** **[`docs/run-playbook.md`](docs/run-playbook.md)**. Atualiza a forge, detecta o seu contexto (novo / continuação / repo externo / atualização da forge) e encaminha para o fluxo certo. Referências de detalhe: [`conductor-run-playbook.pt.md`](docs/conductor-run-playbook.pt.md) (fases A→E) e [`unattended-run-playbook.md`](docs/superpowers/unattended-run-playbook.md) (modo autônomo «lança e volta»).

## Licença

[MIT](LICENSE) © 2026 Digit-AI.

---
*Digit-AI · Consultoria e estratégia de IA · acelerador SaaS · 2026*
