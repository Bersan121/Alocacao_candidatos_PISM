# Análises

Scripts que caracterizam as instâncias e calculam referências exatas para medir a heurística de
`src/`. Usam a mesma lista de instâncias dos experimentos (`instancias/` + `instancias_pism/`, sem
arquivos repetidos) e gravam em `analise/resultados/`. O relatório lê esses CSVs por meio de
`relatorio/gerar_figuras.py`.

| Script | Saída | O que calcula |
|---|---|---|
| `caracteristicas.py` | `caracteristicas.csv` | tamanho, folga de capacidade, demanda por tipo, capacidade de escolas e salas, grupos de candidatos idênticos, pressão de capacidade e LB0 (soma das distâncias à escola mais próxima) |
| `modelo_exato.py [s]` | `modelo_exato.csv` | modelo adotado (um tipo por sala, até K tipos por escola), para K = 1 e K = 2: viabilidade, MIP no HiGHS com limite de `s` segundos por K (padrão 60) e alocação ótima com os tipos da fase A do construtivo; e o limite inferior por transporte (`LB`), comum aos dois K |
| `busca_tipos.py [s]` | `busca_tipos.csv` | referência para K = 1: busca local nos tipos das escolas (mudar o tipo de uma escola, trocar os de duas) com cada vizinho avaliado pela alocação ótima (transporte), partindo dos tipos da melhor solução de `resultados/` (limite de `s` segundos, padrão 120) |
| `comum.py` | — | lista de instâncias, agrupamento de candidatos idênticos, PL de transporte e chamada ao MIP |

```
.venv/bin/python analise/caracteristicas.py
.venv/bin/python analise/modelo_exato.py 60     # ~50 min
.venv/bin/python analise/busca_tipos.py 120     # ~4 min; depois de src/experimentos.py
```

## Colunas de `modelo_exato.csv`

- `LB`: transporte em que a capacidade `Q_j` da escola é compartilhada livremente entre os tipos.
  É limite inferior para K = 1 e para K = 2.
- Para cada K (sufixo `1` ou `2`): `viavel` (as salas podem receber tipos, com até K por escola,
  cobrindo a demanda de cada tipo?), `MIP` (melhor solução em `s` segundos), `MIP_lb` (limite
  inferior do MIP), `MIP_otimo` (1 se o ótimo foi provado), `t_mip` e `aloc_otima` (alocação ótima
  por transporte com os tipos da fase A).
- Com K = 1 o MIP usa a formulação por escola (`y[j,t]`, capacidade `Q_j y[j,t]`), mais compacta;
  com K = 2, variáveis por classe de salas iguais.

## Resultados atuais (28 instâncias, MIP de 60 s)

- **Um tipo por escola (K = 1):** 24 instâncias são viáveis. `instancias/instancia_2`,
  `Instancia1_G2`, `Instancia2_G2` e `Instancia2_G5` não são (em `Instancia2_G2` há só 5 escolas para
  6 tipos; nas outras, nenhuma divisão das escolas inteiras entre os tipos cobre todas as demandas).
  O MIP prova o ótimo em 6 instâncias pequenas e não encontra solução em 60 s em 9 grandes; o `LB`
  de transporte é fraco para K = 1. Por isso a referência inclui `busca_tipos.csv`, que melhora a
  melhor solução da heurística em 20 das 24 instâncias (1,4% em média, até 6,1%).
- **Até dois tipos por escola (K = 2):** 27 instâncias são viáveis; só `Instancia1_G2` não é (nem
  sem limite de tipos por escola). O MIP prova o ótimo em 7 instâncias e fica pior que a heurística
  na maioria das demais.

A referência usada para os gaps da heurística é o menor valor entre `MIP`, `aloc_otima`, `busca_tipos` (K = 1) e a melhor
solução dos experimentos. O limite inferior é o maior valor entre `LB` e `MIP_lb`.

Os valores do MIP dependem do limite de tempo e da máquina, por isso podem variar um pouco de uma
execução para outra.
