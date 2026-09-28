# Formato das Instâncias (.txt)

Esta pasta contém os arquivos de instâncias gerados para o problema de alocação de candidatos. Os arquivos de texto (`.txt`) foram projetados para serem **puramente legíveis por máquina**.

---

## 📐 Estrutura Geral do Arquivo `.txt`

O arquivo é estruturado em duas seções em sequência: **Escolas** e **Candidatos**.

```text
<NUM_ESCOLAS>
<ID_ESCOLA_1> <CEP> <CAPACIDADE_TOTAL> <NUM_SALAS> <CAP_SALA_1> <CAP_SALA_2> ... <CAP_SALA_K>
<ID_ESCOLA_2> <CEP> <CAPACIDADE_TOTAL> <NUM_SALAS> <CAP_SALA_1> <CAP_SALA_2> ... <CAP_SALA_K>
... (exatamente N linhas de escolas)
<NUM_CANDIDATOS>
<ID_CANDIDATO_1> <CEP> <TIPO_PROVA>
<ID_CANDIDATO_2> <CEP> <TIPO_PROVA>
... (exatamente M linhas de candidatos)
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
  2. **`CEP`** (`string` / `int`): CEP numérico do endereço do candidato sem hífen (8 dígitos, ex: `36025001` para JF ou `36200000` para outra cidade).
  3. **`TIPO_PROVA`** (`string`): Código do tipo de prova do candidato (`M1`, `M2`, `M3e`, `M3s`, `M3h`, `M3d`).

---

## 💡 Exemplo Prático Ilustrativo

Abaixo está um exemplo de arquivo contendo 2 escolas e 3 candidatos:

```text
2
1 36036900 300 3 100 100 100
2 36026420 250 2 120 130
3
1 36036900 M1
2 36200000 M3e
3 36025001 M2
```

### Explicação do Exemplo:
- **`2`**: A instância possui 2 escolas.
  - **Escola 1**: ID `1`, CEP `36036900`, Capacidade Total `300`, `3` salas com capacidades `100`, `100` e `100` ($100+100+100 = 300$).
  - **Escola 2**: ID `2`, CEP `36026420`, Capacidade Total `250`, `2` salas com capacidades `120` e `130` ($120+130 = 250$).
- **`3`**: A instância possui 3 candidatos.
  - **Candidato 1**: ID `1`, CEP `36036900`, Prova `M1`.
  - **Candidato 2**: ID `2`, CEP `36200000` (fora de JF), Prova `M3e`.
  - **Candidato 3**: ID `3`, CEP `36025001`, Prova `M2`.
```