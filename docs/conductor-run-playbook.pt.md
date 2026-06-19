# Conductor Run — Playbook do operador

> 🌍 [English](conductor-run-playbook.md) · [Français](conductor-run-playbook.fr.md) · [Español](conductor-run-playbook.es.md) · [Deutsch](conductor-run-playbook.de.md) · [Italiano](conductor-run-playbook.it.md) · [Português](conductor-run-playbook.pt.md)

Este playbook é o prompt do operador para conduzir um `conductor run` de ponta a ponta da
Digit-AI SaaS Forge **a partir de outro projeto Claude Code**, anexando um dossiê de
especificações/restrições. A execução é orquestrada mas **governada**: para em dois checkpoints
humanos (HITL) por concepção e nunca faz merge automático.

## A metodologia em uma tela

```
anexos ─▶ [−1] classificar (escopo vs restrições)
      ─▶ [0]  preflight (gh/token, uv/node, rede, clonar forge)
      ─▶ [A]  enquadramento → MissionConfig (11 bricks build/buy, t0 forçadas)  ⟲ validar
      ─▶ [B]  scaffold-first (copier + bricks, ANTES de qualquer agente)
      ─▶ [C]  planejamento BMAD (epics.md)                                      ⛔ HITL 1
      ─▶ [D]  config de sprint (sprint-status.yaml + bad:, auto_pr_merge=false)
      ─▶ [E]  sprint /bad + duplo gate (código + design) + 3 retries            ⛔ HITL 2
              → Pull Requests PR-ready (nunca mescladas automaticamente)
```

Salvaguardas inegociáveis: **scaffold-first**, **duplo gate** (CI de código + lint de design),
**2 HITL**, **dependências fixadas/vendorizadas** (BAD `@v1.2.0`, `@google/design.md@0.3.0`),
**`auto_pr_merge=false`**.

## O prompt do operador (cole no outro projeto Claude Code)

```markdown
# Missão — Conduzir um `conductor run` (Digit-AI SaaS Forge) da ideia ao PR-ready

Você é o operador da `digit-ai-saas-forge` NESTE projeto. Vai levar um escopo de produto até
Pull Requests PR-ready, orquestrando a cadeia A→E do conductor. Você NÃO está autorizado a
contornar suas salvaguardas.

## Entradas (fornecidas como ANEXOS)
Um ou mais arquivos estão anexados (specs, restrições, notas técnicas — formatos diversos: md,
pdf, docx, txt, imagens). NÃO estão pré-ordenados.

Repo da forge: https://github.com/iguane39/digit-ai-saas-forge
Repo destino das PR (onde o SaaS é gerado): {{ org/repo, ou "a criar" }}

## Fase −1 — Analisar e classificar os anexos
Leia CADA anexo por completo, depois separe o conteúdo em duas categorias — sem inventar nada,
sem perder nada:
- **ESCOPO (o "quê")**: intenção de produto, usuários/personas, funcionalidades, user stories,
  regras de negócio, telas/fluxos, dados, critérios de sucesso de produto.
- **RESTRIÇÕES (o "como / em que quadro")**: stack imposta, integrações, segurança/conformidade
  (LGPD/GDPR, multi-tenancy, RBAC, SSO…), performance, hospedagem, orçamento, prazo, carta/marca
  e design, requisitos de testes/CI, dependências permitidas.
Regras: um requisito ambíguo → coloque em ambas e marque "a arbitrar"; algo que não é nenhuma →
liste como "fora de quadro / ignorar"; se os arquivos se contradizem → reporte o conflito (não
decida sozinho).
→ Produza uma TABELA DE CLASSIFICAÇÃO (Arquivo · Trecho · Categoria · Nota) e AGUARDE minha
validação da ordenação antes do preflight. É a base de todo o resto.

## Salvaguardas (INEGOCIÁVEIS)
- **Scaffold-first**: o esqueleto de produção existe antes de qualquer agente (B antes de C).
- **Duplo gate**: nenhuma história é entregue se a CI de código OU o lint de design falhar.
- **2 HITL**: (1) após o planejamento BMAD, (2) antes de qualquer merge. Em CADA HITL você PARA,
  apresenta um resumo de decisão e AGUARDA minha aprovação explícita. Essas paradas são
  intencionais — não são falhas.
- **`auto_pr_merge=false`**: você NUNCA faz auto-merge. Não se auto-aprova nenhum HITL.
- **Regra de merge**: a integração por EPIC é **automática e local** (apenas se o duplo gate estiver verde); o único merge **humano** é para o GitHub/`main`, **uma vez, no fim** (HITL 2). Uma EPIC bloqueada não é mergeada.
- **Dependências fixadas/vendorizadas**: BAD `@v1.2.0`, `@google/design.md@0.3.0`.
- "Ponta a ponta" = orquestrado sem passo manual FORA dos 2 HITL previstos.

## Fase 0 — Preflight (fail-fast: se um ponto falhar, PARE e diga)
1. `gh auth status` OK e `GITHUB_PERSONAL_ACCESS_TOKEN` exportado (`export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)`).
2. `uv`, `node`/`npx`, `git`, acesso de rede (npx/copier/bmad) disponíveis.
3. Forge acessível: clone-a e `uv sync` em `digitai-saas-forge/`.
4. Confirme o repo destino das PR e a pasta de destino do SaaS gerado.
→ Retorne uma tabela "preflight OK/KO" antes de continuar.

## Fase A — Enquadramento (o mapeamento = o trabalho real)
A partir do ESCOPO + RESTRIÇÕES validados na Fase −1, PROPONHA um `MissionConfig` explícito:
- `idea`: uma frase de síntese (NÃO os anexos inteiros).
- `target`: alvo (padrão `fastapi-saas`).
- `saas_scope`: para CADA um dos 11 bricks, uma decisão `build`/`buy`/`skip` JUSTIFICADA pelos
  anexos. Nota: `multi-tenancy`, `rbac`, `auth-sso` são FORÇADAS a `build` (t0).
- `brand_charter` + `style_slug`: se nenhuma carta for anexada, sinalize e proponha o `DESIGN.md`
  padrão (o lint de design roda sobre ele) — a validar.
- `budget`/`deadline` e `max_parallel_stories` (limite, padrão 2-3) para limitar o custo.
- Liste os requisitos de escopo que você NÃO soube mapear (zona cinzenta).
→ APRESENTE este `MissionConfig` e AGUARDE minha validação antes da Fase B (enquadramento = checkpoint).

## Fase B — Scaffold-first
Gere o esqueleto via `copier` + enxerte os bricks escolhidos (t0 incluídos). Verifique que o
harness CI (gate de código) está no lugar. NÃO invoque nenhum agente antes do fim de B.

**Configuração de partida (roteamento onramp).** O «scaffold-first» generaliza-se num *onramp*
escolhido por `select_onramp` conforme a proveniência do projeto — todos produzem o mesmo substrate,
portanto as Fases C→E são idênticas para as três:
- **From scratch** (`--mode greenfield`) → `ScaffoldOnramp`: gera o esqueleto (esta seção).
- **Continuação** de um projeto gerado pela forge (`--mode brownfield`, repo já conforme) →
  `NoOnramp`: SEM scaffold; captura uma baseline que alimenta o gate de não regressão; planeja
  apenas os epics novos.
- **Projeto externo** (`--mode brownfield`, repo a normalizar) → `AdapterOnramp` (FastAPI incompleto)
  ou `BuilderOnramp` (stack não-FastAPI) + HITL-0 se houver degradação declarada; depois
  `--intent remediation|complement|both`.

## Fase C — Ponte BMAD → HITL 1
`npx bmad-method install --modules bmm,tea`, depois produza o planejamento em
`_bmad-output/planning-artifacts/epics.md` (PRD, arquitetura, épicos, histórias).
→ **HITL 1**: apresente um resumo PRD + arquitetura + épicos/histórias. PARE. Escreva a config de
sprint apenas após meu "go".

## Fase D — Adaptador de sprint
Escreva `_bmad-output/implementation-artifacts/sprint-status.yaml` e a seção `bad:` de
`_bmad/config.yaml` com **`auto_pr_merge: false`**, `max_parallel_stories` limitado, tiers de
modelos. NÃO compile um grafo (BAD o constrói sozinho).

## Fase E — Supervisor (sprint sob o duplo gate)
Invoque o skill `/bad` (1 worktree/história, pipeline de 7 passos, gate de código interno) com
`AUTO_PR_MERGE=false`. Para cada história:
- Gate de design: `npx --yes -p @google/design.md@0.3.0 designmd lint --format json` DEPOIS
  aplique a política de severidade (NÃO confie no exit code: uma falha WCAG pode sair como
  `warning` → exit 0). Bloqueie em contraste/refs/seções faltantes mesmo em `warning`.
- Em caso de falha de um gate: até **3 retries** do agente, senão marque a história `blocked` +
  escale.
→ **HITL 2**: apresente as PR PR-ready (checklist: PR aberta e não mesclada, duplo gate verde,
corpo gerado, issue vinculada, mergeable=clean, atribuída a revisão) e as histórias `blocked`.
PARE. NÃO MESCLE NADA.

## Saída esperada e registro
- Um REGISTRO DE EXECUÇÃO: classificação dos anexos, status por fase, decisões de enquadramento,
  histórias ready vs blocked, links das PR, custo/tempo aproximados, zonas cinzentas.
- Lembre onde vive o SaaS gerado e como RETOMAR após cada HITL.
- Se o escopo for grande: proponha primeiro um slice MVP / primeiro épico, valide-o, depois
  estenda — em vez de disparar todo o sprint de uma vez.

## Proibido (feche as portas)
- Não processe anexos sem tê-los lido e classificado (Fase −1). Não cole um documento inteiro
  como `idea`. Não pule o preflight. Não force `auto_pr_merge=true`. Não se auto-aprove nenhum
  HITL. Não ignore nenhuma restrição sem sinalizá-la na zona cinzenta. Não faça fork de
  BMAD/BAD/o template/design.md.
```

## Ingestão real (piloto)

A ingestão é heurística por padrão (determinística, sem rede). Para ativar o **sub-agente
analisador real** (`claude -p`), defina `CONDUCTOR_USE_CLAUDE_ANALYZER=1` (requer o CLI
`claude` autenticado). O teste de integração condicional documenta o caminho:
`RUN_CLAUDE_INTEGRATION=1 uv run pytest tests/test_claude_integration.py`.

## Sprint autônomo real (`/bad`, piloto)

O sprint BAD autônomo está **desativado por padrão**. Para ativá-lo, defina
`CONDUCTOR_ENABLE_REAL_BAD=1` (requer `claude` e `gh` autenticados). Postura de segurança:
a execução depende do isolamento nativo do BAD (um worktree git por história),
`AUTO_PR_MERGE=false` está bloqueado por tipo (nunca faz auto-merge), e HITL 2 ainda controla
cada merge. `/bad` é executado com `--dangerously-skip-permissions` e isolamento de rede
relaxado — **execute-o apenas em um repositório cuja branch `main` seja protegida; nunca em
código cliente sensível sem revisão.** Os resultados são observados via `gh pr list` (a fonte
da verdade) e mapeados para os resultados por história.

## Planejamento BMAD real (piloto)

O planejamento BMAD é coletado por padrão (`DefaultBmadPlanner` instala o BMAD e lê os
artefatos; HITL 1 pausa se ausente). Para ativar o **planejamento BMAD autônomo** via
`claude -p`, defina `CONDUCTOR_ENABLE_REAL_BMAD=1` (requer `claude` autenticado). Ele produz
apenas documentos de planejamento sob `_bmad-output/planning-artifacts/` e é sempre controlado
por **HITL 1** antes de qualquer desenvolvimento — nenhum código é alterado e nada é mesclado
nesta fase. Com os três opt-ins ativos (`CONDUCTOR_USE_CLAUDE_ANALYZER`,
`CONDUCTOR_ENABLE_REAL_BMAD`, `CONDUCTOR_ENABLE_REAL_BAD`), a cadeia `A→E` completa é
executada de verdade, ainda pausando em ambos os gates HITL.

## Gate de conformidade com o spec real (piloto)

O gate de conformidade com o spec está **desativado por padrão** (o supervisor executa apenas o
duplo gate + a não regressão). Para ativar uma **revisão de conformidade por story** via
`claude -p`, defina `CONDUCTOR_ENABLE_SPEC_REVIEW=1` (requer `claude` autenticado). Ele compara os
critérios de aceitação de cada story com o diff de sua PR: um **under-build** (critério não
cumprido) bloqueia a story (entra na remediação limitada a 3 retries, depois `blocked`); um
**over-build** (comportamento além do spec) é consultivo. Todos os findings são persistidos em
`SPEC_FINDINGS.md` com um status `traité`/`non-traité` para retomada manual posterior. Nenhum merge
é afetado; HITL 2 permanece inalterado.
