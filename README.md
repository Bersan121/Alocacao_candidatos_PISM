# Gerador de Instâncias - Alocação de Candidatos em Escolas (PISM)

Este repositório contém o gerador de instâncias sintéticas para o problema **NP-difícil** de alocação e ensalamento de candidatos em locais de prova (baseado na estrutura do PISM/UFJF).

O script `gerador_instancias.py` cria arquivos de instâncias formatados para leitura por máquinas e solvers de Pesquisa Operacional (em C, C++, Python, Julia, etc.).

---

## 📋 Recursos e Características das Instâncias

- **Escolas**:
  - Número de escolas configurável (padrão: 10 a 20 escolas).
  - Capacidade total por escola configurável (padrão: 200 a 500 alunos).
  - Número de salas por escola configurável (padrão: 5 a 15 salas).
  - Divisão da capacidade da escola entre as salas garantindo que $\sum \text{capacidades\_salas} = \text{capacidade\_total}$.
  - CEPs sorteados a partir da lista oficial de 20 CEPs de escolas de Juiz de Fora (apenas números, sem hífen).

- **Candidatos**:
  - Quantidade total de candidatos ajustável proporcionalmente à capacidade acumulada de todas as escolas (padrão: 80% a 95% de ocupação).
  - CEPs com proporção geográfica configurável (padrão: 80% de Juiz de Fora e 20% de cidades da região/estado).
  - Tipos de prova sorteados entre: `M1`, `M2`, `M3e`, `M3s`, `M3h`, `M3d`.

---

## ⚙️ Variáveis Globais de Configuração

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
| `CEPS_ESCOLAS_JF` | `List[str]` | 20 CEPs | Lista de CEPs numéricos de escolas de JF |
| `CEPS_OUTRAS_CIDADES` | `List[str]` | 11 CEPs | Lista de CEPs numéricos de outras cidades (Barbacena, Ubá, etc.) |
| `TIPOS_PROVA` | `List[str]` | 6 tipos | Tipos de prova (`M1`, `M2`, `M3e`, `M3s`, `M3h`, `M3d`) |

---

## 🚀 Como Executar

### 1. Execução Padrão via Terminal

Para gerar instâncias no formato `.txt` dentro da pasta `instancias/`:

```bash
python3 gerador_instancias.py --qtd 5 --outdir ./instancias --formato txt
```

### 2. Parâmetros da Linha de Comando (CLI)

| Parâmetro | Descrição | Padrão |
|---|---|---|
| `--qtd` | Quantidade de instâncias a serem geradas | `1` |
| `--outdir` | Diretório de destino dos arquivos gerados | `instancias` |
| `--prefixo` | Prefixo do nome dos arquivos (ex: `instancia_1.txt`) | `instancia` |
| `--formato` | Formato de saída (`txt`, `json` ou `ambos`) | `txt` |
| `--seed` | Semente aleatória para reprodutibilidade | `None` |

### Exemplos:

```bash
# Gerar 10 instâncias em texto plano com semente fixa
python3 gerador_instancias.py --qtd 10 --outdir ./instancias --formato txt --seed 12345

# Gerar instâncias salvando tanto em .txt quanto em .json
python3 gerador_instancias.py --qtd 3 --outdir ./instancias --formato ambos
```

---

## 📁 Estrutura do Repositório

```text
.
├── gerador_instancias.py    # Script principal do gerador
├── README.md                # Instruções e documentação geral
└── instancias/              # Pasta contendo os arquivos .txt gerados
    ├── README.md            # Especificação detalhada do formato .txt para parsers
    ├── instancia_1.txt
    ├── instancia_2.txt
    └── ...
```
