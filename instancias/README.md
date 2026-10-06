# Formato das Instâncias (.txt)

Esta pasta contém os arquivos de instâncias gerados para o problema de alocação de candidatos. Os arquivos de texto (`.txt`) foram projetados para serem **puramente legíveis por máquina**, sem cabeçalhos textuais ou linhas de comentários (como `#`), permitindo uma leitura direta e de alto desempenho em linguagens como **C, C++, Python, Julia, Java**, entre outras.

---

## 📐 Estrutura Geral do Arquivo `.txt`

O arquivo é estruturado em três seções em sequência: **Escolas**, **Candidatos** e **Matriz de Distâncias**.

```text
<NUM_ESCOLAS>
<ID_ESCOLA_1> <CEP> <CAPACIDADE_TOTAL> <NUM_SALAS> <CAP_SALA_1> <CAP_SALA_2> ... <CAP_SALA_K>
<ID_ESCOLA_2> <CEP> <CAPACIDADE_TOTAL> <NUM_SALAS> <CAP_SALA_1> <CAP_SALA_2> ... <CAP_SALA_K>
... (exatamente N linhas de escolas)
<NUM_CANDIDATOS>
<ID_CANDIDATO_1> <CEP> <TIPO_PROVA>
<ID_CANDIDATO_2> <CEP> <TIPO_PROVA>
... (exatamente M linhas de candidatos)
<DISTANCIA_CAND_1_ESC_1> <DISTANCIA_CAND_1_ESC_2> ... <DISTANCIA_CAND_1_ESC_N>
<DISTANCIA_CAND_2_ESC_1> <DISTANCIA_CAND_2_ESC_2> ... <DISTANCIA_CAND_2_ESC_N>
... (exatamente M linhas da matriz de distâncias, cada uma com N colunas)
```

---

## 🔍 Detalhamento dos Campos e Ordem dos Conteúdos

### 1. Seção de Escolas

- **Linha 1**: `N` (Inteiro)  
  *Quantidade total de escolas presentes na instância.*

- **Linhas 2 até (N + 1)**: Informações da Escola (Valores separados por espaço simples):
  1. **`ID`** (`int`): Identificador único da escola (iniciando em 1).
  2. **`CEP`** (`string` / `int`): CEP numérico da escola em Juiz de Fora sem hífen (8 dígitos, ex: `36036900`).
  3. **`CAPACIDADE_TOTAL`** (`int`): Capacidade total de alunos que a escola suporta.
  4. **`NUM_SALAS`** (`int`): Quantidade $K$ de salas de prova nesta escola.
  5. **`CAPACIDADE_SALAS`** (`int ... int`): $K$ inteiros representando a capacidade de cada sala da escola.  
     *(Nota: O somatório das capacidades das salas é exatamente igual à `CAPACIDADE_TOTAL`).*

---

### 2. Seção de Candidatos

- **Linha (N + 2)**: `M` (Inteiro)  
  *Quantidade total de candidatos inscritos na instância.*

- **Linhas (N + 3) até (N + M + 2)**: Informações do Candidato (Valores separados por espaço simples):
  1. **`ID`** (`int`): Identificador único do candidato (iniciando em 1).
  2. **`CEP`** (`string` / `int`): CEP numérico do endereço do candidato sem hífen (8 dígitos, ex: `36025001` para JF ou `36200010` para outra cidade).
  3. **`TIPO_PROVA`** (`string`): Código do tipo de prova do candidato (`M1`, `M2`, `M3e`, `M3s`, `M3h`, `M3d`).

---

### 3. Seção da Matriz de Distâncias

- **Linhas (N + M + 3) até (N + 2*M + 2)**: Linhas da Matriz de Distâncias ($M \times N$ floats):
  - Cada linha $i$ (correspondente ao candidato $i$) possui $N$ valores de ponto flutuante separados por espaço.
  - O $j$-ésimo valor da linha $i$ representa a **Distância Euclidiana** entre as coordenadas de geolocalização do Candidato $i$ e da Escola $j$.

---

## 💡 Exemplo Prático Ilustrativo

Abaixo está um exemplo de arquivo contendo 2 escolas e 3 candidatos:

```text
2
1 36036900 300 3 100 100 100
2 36026420 250 2 120 130
3
1 36036900 M1
2 36200010 M3e
3 36025001 M2
0.0 0.0
0.684849 0.684849
0.005792 0.005792
```

### Explicação do Exemplo:
- **`2`**: A instância possui 2 escolas.
- **Escola 1 e Escola 2**: Dados de ID, CEP, Capacidade total, Número de salas e capacidades das salas.
- **`3`**: A instância possui 3 candidatos.
- **Matriz de Distâncias**: 3 linhas (uma por candidato) x 2 colunas (uma por escola).
  - Linha 1 (`0.0 0.0`): Distância do Candidato 1 às escolas 1 e 2.
  - Linha 2 (`0.684849 0.684849`): Distância do Candidato 2 (fora de JF) às escolas 1 e 2.
  - Linha 3 (`0.005792 0.005792`): Distância do Candidato 3 às escolas 1 e 2.

---

## 💻 Exemplos de Leitura de Código

### Exemplo em C++

```cpp
#include <iostream>
#include <fstream>
#include <vector>
#include <string>

struct Escola {
    int id;
    std::string cep;
    int capacidade_total;
    int num_salas;
    std::vector<int> capacidade_salas;
};

struct Candidato {
    int id;
    std::string cep;
    std::string tipo_prova;
};

void lerInstancia(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) return;

    // 1. Ler Escolas
    int num_escolas;
    file >> num_escolas;
    std::vector<Escola> escolas(num_escolas);

    for (int i = 0; i < num_escolas; ++i) {
        file >> escolas[i].id >> escolas[i].cep >> escolas[i].capacidade_total >> escolas[i].num_salas;
        escolas[i].capacidade_salas.resize(escolas[i].num_salas);
        for (int j = 0; j < escolas[i].num_salas; ++j) {
            file >> escolas[i].capacidade_salas[j];
        }
    }

    // 2. Ler Candidatos
    int num_candidatos;
    file >> num_candidatos;
    std::vector<Candidato> candidatos(num_candidatos);

    for (int i = 0; i < num_candidatos; ++i) {
        file >> candidatos[i].id >> candidatos[i].cep >> candidatos[i].tipo_prova;
    }

    // 3. Ler Matriz de Distâncias (M x N)
    std::vector<std::vector<double>> distancias(num_candidatos, std::vector<double>(num_escolas));
    for (int i = 0; i < num_candidatos; ++i) {
        for (int j = 0; j < num_escolas; ++j) {
            file >> distancias[i][j];
        }
    }

    std::cout << "Instancia lida: " << escolas.size() << " escolas, " 
              << candidatos.size() << " candidatos, matriz " 
              << distancias.size() << "x" << distancias[0].size() << ".\n";
}
```

### Exemplo em Python

```python
def ler_instancia(filepath):
    with open(filepath, 'r') as f:
        lines = f.read().splitlines()

    idx = 0
    num_escolas = int(lines[idx])
    idx += 1

    escolas = []
    for _ in range(num_escolas):
        parts = lines[idx].split()
        escolas.append({
            "id": int(parts[0]),
            "cep": parts[1],
            "capacidade_total": int(parts[2]),
            "num_salas": int(parts[3]),
            "capacidade_salas": [int(x) for x in parts[4:]]
        })
        idx += 1

    num_candidatos = int(lines[idx])
    idx += 1

    candidatos = []
    for _ in range(num_candidatos):
        parts = lines[idx].split()
        candidatos.append({
            "id": int(parts[0]),
            "cep": parts[1],
            "tipo_prova": parts[2]
        })
        idx += 1

    matriz_distancias = []
    for _ in range(num_candidatos):
        linha = [float(x) for x in lines[idx].split()]
        matriz_distancias.append(linha)
        idx += 1

    return escolas, candidatos, matriz_distancias
```