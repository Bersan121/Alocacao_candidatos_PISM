# Análises

Scripts que caracterizam as instâncias e calculam referências exatas para medir a heurística de
`src/`. Usam a mesma lista de instâncias dos experimentos (`instancias/` + `instancias_pism/`, sem
arquivos repetidos) e gravam em `analise/resultados/`. O relatório lê esses CSVs por meio de
`relatorio/gerar_figuras.py`.

| Script | Saída | O que calcula |
|---|---|---|
| `caracteristicas.py` | `caracteristicas.csv` | tamanho, folga de capacidade, demanda por tipo, capacidade de escolas e salas, grupos de candidatos idênticos, pressão de capacidade e LB0 (soma das distâncias à escola mais próxima) |
| `modelo_sala.py [s]` | `modelo_sala.csv` | modelo adotado (um tipo por sala): viabilidade, limite inferior por transporte, MIP no HiGHS com limite de `s` segundos (padrão 60) e alocação ótima com os tipos de sala da fase A do construtivo |
| `modelo_escola.py [s]` | `modelo_escola.csv` | interpretação alternativa (um tipo por escola): viabilidade, MIP e uma heurística (cobertura gulosa + busca nos tipos avaliada por transporte) |
| `comum.py` | — | lista de instâncias, agrupamento de candidatos idênticos, PL de transporte e chamada ao MIP |

```
.venv/bin/python analise/caracteristicas.py
.venv/bin/python analise/modelo_sala.py 60      # ~25 min
.venv/bin/python analise/modelo_escola.py 60    # ~25 min
```

## Resultados atuais (28 instâncias, MIP de 60 s)

- **Um tipo por sala:** 27 instâncias são viáveis. `Instancia1_G2` não é: quatro tipos precisam de
  17 vagas e só há quatro salas de 6. O MIP prova o ótimo em 7 instâncias. Nas demais, devolve a
  melhor solução encontrada e um limite inferior (`MIP_lb`).
- **Um tipo por escola:** 24 instâncias são viáveis e o MIP prova o ótimo em 6. Esse modelo dá
  distâncias bem maiores, como mostra a Seção 8.7 do relatório.
- A referência usada para os gaps da heurística é o menor valor entre `MIP`, `aloc_otima` e a melhor
  solução dos experimentos. O limite inferior é o maior valor entre `LB` e `MIP_lb`.
- **Até dois tipos por sala** (`src/experimentos.py -t 2`): não há MIP para essa variante. O `LB`
  (capacidade da escola compartilhada livremente entre os tipos) continua sendo um limite inferior
  válido, e é a única referência usada para ela no relatório. `Instancia1_G2` não tem `LB` no CSV
  (é inviável com um tipo por sala); `relatorio/gerar_figuras.py` calcula a mesma relaxação para ela.

Os valores do MIP dependem do limite de tempo e da máquina, por isso podem variar um pouco de uma
execução para outra.
