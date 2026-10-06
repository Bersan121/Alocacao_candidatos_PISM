# Formato das Instâncias (.txt)

Esta pasta contém os arquivos de instâncias gerados para o problema de alocação de candidatos, formatados **rigorosamente de acordo com o modelo padrão oficial do projeto**.

---

## 📐 Estrutura Geral do Arquivo `.txt`

```text
NUM_CANDIDATOS: <M>
NUM_ESCOLAS: <N>

# CANDIDATOS (id, CEP, tipo_prova, latitude, longitude)
C1, <CEP>, <TIPO_PROVA>, <LATITUDE>, <LONGITUDE>
C2, <CEP>, <TIPO_PROVA>, <LATITUDE>, <LONGITUDE>
... (M linhas de candidatos)

# ESCOLAS (id, CEP, latitude, longitude, num_salas, capacidades_salas)
E1, <CEP>, <LATITUDE>, <LONGITUDE>, <NUM_SALAS>, <CAP1;CAP2;...;CAPk>
E2, <CEP>, <LATITUDE>, <LONGITUDE>, <NUM_SALAS>, <CAP1;CAP2;...;CAPk>
... (N linhas de escolas)

# MATRIZ_DISTANCIAS (linhas=candidatos, colunas=escolas, em km)
<DIST_C1_E1>, <DIST_C1_E2>, ..., <DIST_C1_EN>
<DIST_C2_E1>, <DIST_C2_E2>, ..., <DIST_C2_EN>
... (M linhas da matriz de distâncias em graus)
```

---

## 🔍 Detalhamento dos Campos

### 1. Cabeçalho
- **`NUM_CANDIDATOS`**: Quantidade total de candidatos $M$.
- **`NUM_ESCOLAS`**: Quantidade total de escolas $N$.

### 2. Seção `# CANDIDATOS`
Cada linha contém as 5 informações do candidato separadas por vírgula e espaço (`, `):
1. **`id`**: Identificador do candidato prefixado com `C` (ex: `C1`, `C2`, ..., `CM`).
2. **`CEP`**: CEP numérico sem hífen (8 dígitos, ex: `36037941`).
3. **`tipo_prova`**: Tipo da prova (`M1`, `M2`, `M3e`, `M3s`, `M3h`, `M3d`).
4. **`latitude`**: Coordenada de latitude (`float` com 6 casas decimais).
5. **`longitude`**: Coordenada de longitude (`float` com 6 casas decimais).

### 3. Seção `# ESCOLAS`
Cada linha contém as 6 informações da escola separadas por vírgula e espaço (`, `):
1. **`id`**: Identificador da escola prefixado com `E` (ex: `E1`, `E2`, ..., `EN`).
2. **`CEP`**: CEP numérico sem hífen (8 dígitos, ex: `36100538`).
3. **`latitude`**: Coordenada de latitude (`float` com 6 casas decimais).
4. **`longitude`**: Coordenada de longitude (`float` com 6 casas decimais).
5. **`num_salas`**: Número $K$ de salas de prova disponíveis na escola.
6. **`capacidades_salas`**: Capacidades das $K$ salas separadas por ponto-e-vírgula (`;`) sem espaço (ex: `8;8` ou `7;11;4`).

### 4. Seção `# MATRIZ_DISTANCIAS`
- Matriz $M \times N$ em que cada linha $i$ contém $N$ distâncias separadas por vírgula e espaço (`, `).
- Os valores são calculados em **graus geográficos** (Distância Euclidiana entre as coordenadas GPS).

---

## 💡 Exemplo Ilustrativo

```text
NUM_CANDIDATOS: 3
NUM_ESCOLAS: 2

# CANDIDATOS (id, CEP, tipo_prova, latitude, longitude)
C1, 36037941, M3h, -21.779531, -43.376217
C2, 36037659, M3e, -21.779505, -43.376256
C3, 36088574, M1, -21.763683, -43.395107

# ESCOLAS (id, CEP, latitude, longitude, num_salas, capacidades_salas)
E1, 36100538, -21.756893, -43.289668, 2, 8;8
E2, 36026213, -21.769287, -43.352413, 2, 15;12

# MATRIZ_DISTANCIAS (linhas=candidatos, colunas=escolas, em km)
0.089472, 0.026071
0.089498, 0.025983
0.107021, 0.043126
```

---

## 💻 Exemplo de Leitura em Python

```python
def ler_instancia_padrao(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    
    num_cand = int(lines[0].split(":")[1].strip())
    num_esc = int(lines[1].split(":")[1].strip())

    candidatos = []
    escolas = []
    matriz_distancias = []

    sec = None
    for line in lines[2:]:
        if line.startswith("# CANDIDATOS"):
            sec = "candidatos"
            continue
        elif line.startswith("# ESCOLAS"):
            sec = "escolas"
            continue
        elif line.startswith("# MATRIZ_DISTANCIAS"):
            sec = "matriz"
            continue

        if sec == "candidatos":
            parts = [p.strip() for p in line.split(",")]
            candidatos.append({
                "id": parts[0],
                "cep": parts[1],
                "tipo_prova": parts[2],
                "latitude": float(parts[3]),
                "longitude": float(parts[4])
            })
        elif sec == "escolas":
            parts = [p.strip() for p in line.split(",")]
            escolas.append({
                "id": parts[0],
                "cep": parts[1],
                "latitude": float(parts[2]),
                "longitude": float(parts[3]),
                "num_salas": int(parts[4]),
                "capacidades_salas": [int(x) for x in parts[5].split(";")]
            })
        elif sec == "matriz":
            linha_dist = [float(x.strip()) for x in line.split(",")]
            matriz_distancias.append(linha_dist)

    return candidatos, escolas, matriz_distancias
```