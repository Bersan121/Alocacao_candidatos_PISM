# Localização de Locais de Prova (PISM) — DCC136, Trabalho 1

Heurística construtiva + busca local (VND) para o problema de localização de locais de prova, uma
variante do *Single Source Capacitated Facility Location Problem*: cada candidato vai para uma
escola, cada **sala** aplica um único tipo de prova (M1, M2, M3e, M3s, M3h, M3d), cada **escola**
oferece **no máximo 1 ou 2 tipos** (parâmetro `--tipos-por-escola`) e o objetivo é minimizar a
distância total. O relatório técnico (modelo SBC) está em `relatorio/relatorio.pdf`.

## Como executar

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# resumo das instâncias
.venv/bin/python src/instancia.py instancias instancias_pism

# experimento principal: construtivo + VND, 10 execuções por instância, RCL k = 10, 1 tipo por escola
.venv/bin/python src/experimentos.py
# o mesmo com até 2 tipos de prova por escola (grava em resultados/tipos2/)
.venv/bin/python src/experimentos.py -t 2
# uma instância, com o passo a passo (fase A, fase B e cada movimento do VND)
.venv/bin/python src/experimentos.py -r 1 --traco -o resultados/exemplo instancias_pism/instancia1_G8.txt
.venv/bin/python src/experimentos.py -t 2 -r 1 --traco -o resultados/tipos2/exemplo instancias_pism/instancia1_G8.txt
```

Opções de `src/experimentos.py`: `-r` execuções (sementes 0..r-1), `-k` tamanho da RCL (`k = 1` é
determinístico), `-t`/`--tipos-por-escola` máximo de tipos de prova por escola (1 ou 2; padrão 1),
`--limite S` limite de tempo do VND, `--sem-busca` só o construtivo, `--traco` passo a passo, `-o`
pasta de saída. Saídas em `resultados/` (ou `resultados/tipos2/` com `-t 2`):

| Arquivo | Conteúdo |
|---|---|
| `execucoes.csv` | uma linha por execução: valor inicial e final, melhoria, tempos, escolas/salas usadas, movimentos e ganho de cada vizinhança |
| `resumo.csv` | por instância: média, desvio, melhor e pior do valor inicial e final, melhoria e tempo médios |
| `solucoes/<pasta>/<inst>.txt` | melhor solução: tipo e ocupação de cada sala e escola/sala de cada candidato |
| `solucoes/<pasta>/<inst>_distribuicao.csv` | candidatos, capacidade e distância média por escola e tipo |
| `traco/<pasta>/<inst>.txt` | passo a passo (com `--traco`) |

As análises das instâncias (características, limite inferior e MIP) estão em `analise/` (ver
`analise/README.md`). O relatório é gerado por:

```bash
.venv/bin/python relatorio/gerar_figuras.py     # figuras (PNG), tabelas e números citados no texto
cd relatorio && latexmk -pdf relatorio.tex
```

As figuras do relatório são sempre imagens PNG (300 dpi) em `relatorio/figuras/`, nunca PDF.

## Estrutura

```text
.
├── src/
│   ├── instancia.py        # leitura das instâncias, lista sem repetidos, resumo
│   ├── solucao.py          # representação (tipo de cada sala + escola de cada candidato), avaliação, verificação
│   ├── construtivo.py      # fase A (tipos das escolas e das salas) + fase B (arrependimento estático com RCL)
│   ├── busca_local.py      # VND: shift, swap, cadeias de ejeção, retipar sala, trocar salas, tipo da escola, trocar escolas
│   └── experimentos.py     # roda tudo e grava resultados/
├── analise/                # caracterização das instâncias e referências exatas
├── resultados/             # saídas dos experimentos (principal, exemplo, sensibilidade a k e tipos2/)
├── relatorio/              # relatório SBC (LaTeX), figuras (PNG) e tabelas
├── instancias/             # instâncias do grupo + especificação do formato
├── instancias_pism/        # instâncias oficiais da turma (um par por grupo)
├── gerador_instancias.py   # gerador de instâncias do grupo (abaixo)
├── cep_cache.json          # cache de geolocalização dos CEPs
└── trabalho.pdf            # enunciado
```

---

## Gerador de instâncias

Este repositório contém o gerador de instâncias sintéticas para o problema **NP-difícil** de alocação e ensalamento de candidatos em locais de prova (baseado na estrutura do PISM/UFJF).

O script `gerador_instancias.py` cria arquivos de instâncias formatados estritamente conforme o modelo padronizado do projeto, contendo candidatos, escolas e a **Matriz de Distâncias Geográficas em Graus (Candidatos x Escolas)** baseada em CEP.

---

### 📋 Recursos e Características das Instâncias

- **Escolas**:
  - Número de escolas configurável (padrão: 10 a 20 escolas).
  - Capacidade total por escola configurável (padrão: 200 a 500 alunos).
  - Número de salas por escola configurável (padrão: 5 a 15 salas).
  - Divisão da capacidade da escola entre as salas garantindo que $\sum \text{capacidades\_salas} = \text{capacidade\_total}$.
  - CEPs sorteados a partir da lista oficial de 20 CEPs de escolas de Juiz de Fora (apenas números, sem hífen).
  - Identificadores prefixados: `E1`, `E2`, ..., `EN`.

- **Candidatos**:
  - Quantidade total de candidatos ajustável proporcionalmente à capacidade acumulada de todas as escolas (padrão: 80% a 95% de ocupação).
  - CEPs com proporção geográfica configurável (padrão: 80% de Juiz de Fora e 20% de cidades da região/estado).
  - Tipos de prova sorteados entre: `M1`, `M2`, `M3e`, `M3s`, `M3h`, `M3d`.
  - Identificadores prefixados: `C1`, `C2`, ..., `CM`.

- **Matriz de Distâncias e Geolocalização**:
  - Geolocalização dos CEPs obtida via API (**BrasilAPI v2** com fallback para **ViaCEP + OpenStreetMap/Nominatim**).
  - **Cache Local (`cep_cache.json`)**: Cada CEP consultado é armazenado em disco para evitar requisições repetidas à API em novas execuções.
  - **Distância Euclidiana em Graus**: Matriz $M \times N$ em que a linha $i$ contém a distância euclidiana das coordenadas (latitude, longitude) do candidato $i$ para todas as $N$ escolas.

---

### ⚙️ Variáveis Globais de Configuração

As principais faixas e taxas podem ser alteradas diretamente no início do arquivo `gerador_instancias.py`:

| Variável | Tipo | Valor Padrão | Descrição |
|---|---|---|---|
| `MIN_ESCOLAS` | `int` | `10` | Quantidade mínima de escolas por instância |
| `MAX_ESCOLAS` | `int` | `20` | Quantidade máxima de escolas por instância |
| `MIN_CAPACIDADE_ESCOLA` | `int` | `200` | Capacidade mínima de alunos por escola |
| `MAX_CAPACIDADE_ESCOLA` | `int` | `500` | Capacidade máxima de alunos por escola |
| `MIN_SALAS_POR_ESCOLA` | `int` | `5` | Número mínimo de salas por escola |
| `MAX_SALAS_POR_ESCOLA` | `int` | `15` | Número máximo de salas por escola |
| `MIN_PCT_CANDIDATOS` | `float` | `0.80` | Taxa de ocupação mínima (80% da capacidade total) |
| `MAX_PCT_CANDIDATOS` | `float` | `0.95` | Taxa de ocupação máxima (95% da capacidade total) |
| `PCT_CANDIDATOS_JF` | `float` | `0.80` | Proporção de alunos com CEP em Juiz de Fora (80%) |
| `CEP_CACHE_FILE` | `str` | `"cep_cache.json"` | Arquivo local de armazenamento de latitude/longitude |
| `CEPS_ESCOLAS_JF` | `List[str]` | 20 CEPs | Lista de CEPs numéricos de escolas de JF |
| `CEPS_OUTRAS_CIDADES` | `List[str]` | 11 CEPs | Lista de CEPs numéricos de outras cidades (Barbacena, Ubá, etc.) |
| `TIPOS_PROVA` | `List[str]` | 6 tipos | Tipos de prova (`M1`, `M2`, `M3e`, `M3s`, `M3h`, `M3d`) |

---

### 🚀 Como Executar

#### 1. Execução Padrão via Terminal

Para gerar instâncias no formato `.txt` padronizado dentro da pasta `instancias/`:

```bash
python3 gerador_instancias.py --qtd 5 --outdir ./instancias --formato txt
```

#### 2. Parâmetros da Linha de Comando (CLI)

| Parâmetro | Descrição | Padrão |
|---|---|---|
| `--qtd` | Quantidade de instâncias a serem geradas | `1` |
| `--outdir` | Diretório de destino dos arquivos gerados | `instancias` |
| `--prefixo` | Prefixo do nome dos arquivos (ex: `instancia_1.txt`) | `instancia` |
| `--formato` | Formato de saída (`txt`, `json` ou `ambos`) | `txt` |
| `--seed` | Semente aleatória para reprodutibilidade | `None` |
| `--cache` | Caminho do arquivo JSON de cache de CEPs | `cep_cache.json` |
