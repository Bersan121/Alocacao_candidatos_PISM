# CLAUDE.md

Trabalho 1 de **DCC136 – Inteligência Computacional (UFJF, 2026.3)**

## O que deve ser feito

Uma **heurística construtiva + busca local** para o *Problema de Localização de Locais de Prova*
(vestibular/PISM). A referência é Oliveira, Martinelli Pinto & Milanez (2021), *Solving a university
admission exam location problem: An application in Brazil* (PUC-Rio), disponível em
https://www.maxwell.vrac.puc-rio.br/52465/52465.PDF. O problema é uma variante do
**Single Source Capacitated Facility Location Problem (SSCFLP)**.

### Problema
- Conjuntos: candidatos `C`, locais (escolas) `L`, tipos de prova `T` = {`M1`, `M2`, `M3e`, `M3s`, `M3h`, `M3d`}.
- Dados: distância `d_ij` (candidato i → local j), capacidade `Q_j`, tipo de prova de cada candidato.
- Decisões: (1) **quais locais abrir** e (2) **a qual local cada candidato vai**.
- Restrições:
  - cada candidato vai para **exatamente um** local;
  - cada local oferece **um único tipo de prova**, e o candidato só pode ir para um local do seu tipo;
  - o local não pode receber mais candidatos que `Q_j` (capacidade = soma das capacidades das salas).
- Objetivo: **minimizar a distância total** candidato → local atribuído.

### Componentes obrigatórios
1. **Construtivo** que gere uma solução inicial viável. O relatório precisa explicar: o critério de
   seleção dos locais, a ordem em que os candidatos são considerados, como eles são alocados, como a
   capacidade é tratada, como a compatibilidade de tipo é garantida e o que acontece quando uma
   escolha que parecia boa no início trava a construção. A descrição tem que permitir reproduzir o
   método.
2. **Pelo menos uma estrutura de vizinhança**, escolhida e justificada a partir da representação adotada.
3. **Pelo menos uma busca local** (por exemplo, first ou best improvement) usando essa vizinhança.
4. **Função de avaliação** bem definida: distância total e, se houver penalização de soluções
   inviáveis, quais restrições podem ser violadas, como a penalidade é calculada e por que os
   parâmetros têm esses valores.

### Experimentos (mínimo exigido)
- Valor da solução inicial, valor após a busca local, melhoria obtida e tempo de execução.
- Informações da solução: número de locais usados e distribuição dos candidatos.
- Se houver aleatoriedade: **várias execuções**, com medidas de variabilidade (média, desvio, melhor, pior).

### Entregáveis
- Código-fonte e os arquivos necessários para rodar os experimentos.
- **Relatório técnico em PDF**, escrito em **LaTeX no modelo de artigo da SBC**.
- **Apresentação oral** de 8 a 12 min cobrindo: problema e motivação, representação, construtivo,
  vizinhança e busca local, exemplo passo a passo numa instância pequena, um caso em que a abordagem
  vai mal (e por quê), resultados, conclusões, dificuldades e melhorias possíveis.

O enunciado pede que o foco esteja na **discussão e justificativa das decisões**.

## Estrutura do repositório

```
gerador_instancias.py   # gerador de instâncias do grupo (doc em README.md)
cep_cache.json          # cache de geolocalização dos CEPs usado pelo gerador
instancias/             # instâncias do grupo (= G3 da turma) + README.md com o formato
instancias_pism/        # instâncias oficiais da turma, um par por grupo (G1 a G14)
src/                    # heurística: leitor, solução, construtivo, VND e experimentos
analise/                # caracterização das instâncias e referências exatas (MIP/LB); README.md
resultados/             # saídas de src/experimentos.py (não editar à mão)
relatorio/              # relatório SBC: relatorio.tex, gerar_figuras.py -> figuras/, tabelas/
requirements.txt        # numpy, scipy, matplotlib
trabalho.pdf            # enunciado
```

## Instâncias

`instancias_pism/` tem as instâncias oficiais da turma (versão de 28/10/2026), todas no formato de
`instancias/README.md` e todas sem tipo nas escolas (o tipo das salas é decisão do modelo). Com
`instancias/` são 28 instâncias distintas: 100 a 6798 candidatos e 5 a 20 escolas.
- `Instancia1_G6`/`Instancia2_G6` trazem `NUM_CANDIDATOS: <M> NUM_ESCOLAS: <N>` na mesma linha.
- IDs podem ter zeros à esquerda ou vir fora de ordem (a linha i da matriz é o i-ésimo candidato do
  arquivo); CEP com hífen.
- A unidade da matriz varia (km ou graus). **Use a matriz como está**, sem converter.
- `Instancia1_G3`/`Instancia2_G3` são iguais a `instancias/instancia_1`/`instancia_2`; o código lê
  `instancias/` primeiro e descarta arquivos de conteúdo repetido (por md5).
- `Instancia1_G7(1)` é a instância 1 do G7 (o envio original sem o "(1)" não tinha dados e foi removido).
- `Instancia1_G2` (100 candidatos, 20 salas de 5 ou 6 lugares) é **inviável** mesmo com um tipo por
  sala: quatro tipos precisam de 17 vagas e só há quatro salas de 6.

## Modelo adotado

**Um tipo de prova por sala**: o "local de prova" é a sala; uma escola pode receber vários tipos.
Justificativa e comparação com "um tipo por escola" no relatório (Seções 2.2 e 8.7). Não há
penalização: todas as soluções geradas são viáveis.

Variante opcional `--tipos-por-sala 2` (`-t 2`): uma sala pode ser dividida entre **até dois tipos**
(parte das vagas para cada um). Com `-t 1` (padrão) o código se comporta exatamente como antes
(mesmos valores, soluções e traços). Com `-t 2` todas as 28 instâncias são viáveis (inclusive
`Instancia1_G2`). O experimento principal do relatório usa `-t 1` (`resultados/`); a Seção
"Até dois tipos por sala" compara com `-t 2` (`resultados/tipos2/`).

## Código (Python 3)

Ambiente: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. O scipy traz o
solver HiGHS, usado só nas análises.

- `src/instancia.py`: `ler_instancia(caminho)` devolve uma `Instancia` (`candidatos`, `escolas` com
  a lista de `salas`, matriz `D` M x N, vetores `tipo_cand` e `cap`, `demanda()`, `num_salas`). Tipos
  de prova viram índices 0..5 (`NOMES_TIPOS`). Erros: `ErroInstancia("arquivo:linha: motivo")`.
  `listar_instancias()` lista `instancias/` + `instancias_pism/` sem repetidos e `rotulo(arq)` dá o
  nome usado em todos os resultados (caminho relativo sem `.txt`, ex.: `instancias_pism/Instancia1_G1`).
  Resumo: `.venv/bin/python src/instancia.py instancias instancias_pism`.
- `src/solucao.py`: `Solucao(inst, st, aloc, max_tipos)` mantém `cap[j,t]`, `carga[j,t]` e `custo`.
  `st = (tipo_sala, tipo2, vagas2)`: tipo principal, segundo tipo (-1 = nenhum) e vagas do segundo
  tipo em cada sala; `assentos(j, r)` dá `{tipo: vagas}` e `mover_assentos(j, r, u, t, L)` passa
  vagas de um tipo para outro.
  `verificar()` checa todas as restrições do zero; `distribuir_salas()` põe os candidatos nas salas.
- `src/construtivo.py`: `construir(inst, k, rng, traco, max_tipos)`; `fase_a` devolve `(st, retipagens)`. Fase A: tipo das salas (demanda estimada,
  best-fit, sobras, cobertura; lança `ErroConstrucao` se a instância é inviável). Fase B: fila por
  arrependimento estático, RCL dos k primeiros, aloca na escola mais próxima com sala do tipo e vaga.
- `src/busca_local.py`: `BuscaLocal(sol).vnd()`. N1 shift, N2 swap, N3 cadeias de ejeção (ciclo
  negativo), N4 retipar sala, N5 trocar tipos de duas salas e, só com 2 tipos por sala, N6 dividir
  sala (passa parte das vagas para outro tipo); volta para N1 sempre que melhora.
- `src/experimentos.py [-r 10] [-k 10] [-t 1|2] [--traco] [--sem-busca] [--limite S] [-o resultados] [instancias...]`:
  grava `execucoes.csv`, `resumo.csv`, `solucoes/<pasta>/<inst>.txt` e `_distribuicao.csv` e, com
  `--traco`, `traco/<pasta>/<inst>.txt`. Com `-t 2` a saída padrão é `resultados/tipos2/`.

## Reproduzir tudo

```
.venv/bin/python src/experimentos.py                                     # resultados/ (~15 min)
.venv/bin/python src/experimentos.py -t 2                                # resultados/tipos2/ (~15 min)
.venv/bin/python src/experimentos.py -r 1 --traco -o resultados/exemplo instancias_pism/instancia1_G8.txt
.venv/bin/python src/experimentos.py -t 2 -r 1 --traco -o resultados/tipos2/exemplo instancias_pism/instancia1_G8.txt
for K in 1 5 25 50; do .venv/bin/python src/experimentos.py -k $K -o resultados/sensibilidade_k/k$K; done
.venv/bin/python analise/caracteristicas.py                              # analise/resultados/
.venv/bin/python analise/modelo_sala.py 60                               # MIP de 60 s por instância
.venv/bin/python analise/modelo_escola.py 60
.venv/bin/python relatorio/gerar_figuras.py                              # figuras PNG, tabelas e métricas
cd relatorio && latexmk -pdf relatorio.tex
```

## Relatório

- `relatorio/relatorio.tex` usa o modelo oficial da SBC (`sbc-template.sty`, `sbc.bst`).
- **Figuras sempre como imagens PNG** (300 dpi, função `salvar` em `gerar_figuras.py`), nunca PDF;
  o script apaga PDFs antigos de `relatorio/figuras/`.
- `gerar_figuras.py` lê `resultados/` (1 tipo por sala) e `resultados/tipos2/` (até 2 tipos). O LB
  de `modelo_sala.csv` também vale para 2 tipos; para `Instancia1_G2` (sem LB no CSV, inviável com
  1 tipo) o script calcula a mesma relaxação.
- Todos os números do texto vêm de macros em `relatorio/tabelas/metricas.tex`, geradas por
  `gerar_figuras.py` (não editar à mão). As instâncias citadas ficam no dicionário `CITADAS`.
  Ao mudar resultados, rode o script e confira as frases do texto que interpretam os números.
- Não carregar `hyperref`: com ele o `sbc-template.sty` redefine `\@` e quebra o `babel`.
- Na BasicTeX faltam `titlesec`, `courier`, `helvetic` e `times` (`tlmgr --usermode install ...`).
- Pendências: nomes dos autores; confirmar com o professor a interpretação "local = sala".
