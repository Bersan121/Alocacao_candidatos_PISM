"""Leitura das instâncias do problema de localização de locais de prova.

Formato (o de instancias/README.md), campos separados por vírgula:

    NUM_CANDIDATOS: <M>
    NUM_ESCOLAS: <N>                      (o G6 traz as duas contagens na mesma linha)
    # CANDIDATOS (id, CEP, tipo_prova, latitude, longitude)
    C1, 36024486, M2, -21.787787, -43.341889
    # ESCOLAS (id, CEP, latitude, longitude, num_salas, capacidades_salas)
    E1, 36036894, -21.780664, -43.362510, 3, 30;30;25
    # MATRIZ_DISTANCIAS (linhas=candidatos, colunas=escolas)
    6.9539, 4.3839, ...                   (M linhas com N valores)

A linha i da matriz corresponde ao i-ésimo candidato do arquivo. A unidade das distâncias varia
entre as instâncias (km ou graus) e a matriz é usada como está.

`ler_instancia(caminho)` devolve uma `Instancia`; em caso de erro lança `ErroInstancia` com a
mensagem "arquivo:linha: motivo". `listar_instancias(caminhos)` devolve os arquivos .txt das
pastas dadas sem conteúdo repetido, e `rotulo(arquivo)` o nome usado nos resultados.

Como programa, imprime um resumo de cada instância:

    python src/instancia.py <instancia_ou_pasta> [...]
"""
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
PASTAS_PADRAO = [RAIZ / "instancias", RAIZ / "instancias_pism"]

# Tipos de prova do PISM. O índice do tipo (0..NUM_TIPOS-1) é usado em todo o código.
NOMES_TIPOS = ("M1", "M2", "M3e", "M3s", "M3h", "M3d")
NUM_TIPOS = len(NOMES_TIPOS)


class ErroInstancia(Exception):
    pass


@dataclass
class Candidato:
    id: str
    cep: str
    tipo: int          # índice em NOMES_TIPOS
    lat: float
    lon: float


@dataclass
class Escola:
    id: str
    cep: str
    lat: float
    lon: float
    salas: list        # capacidade de cada sala

    @property
    def capacidade(self):
        return sum(self.salas)


@dataclass
class Instancia:
    arquivo: str
    candidatos: list
    escolas: list
    D: np.ndarray      # M x N: D[i, j] = distância do candidato i à escola j

    def __post_init__(self):
        self.tipo_cand = np.array([c.tipo for c in self.candidatos], dtype=int)
        self.cap = np.array([e.capacidade for e in self.escolas], dtype=int)

    @property
    def nome(self):
        return Path(self.arquivo).stem

    @property
    def M(self):
        return len(self.candidatos)

    @property
    def N(self):
        return len(self.escolas)

    @property
    def num_salas(self):
        return sum(len(e.salas) for e in self.escolas)

    def demanda(self):
        """Número de candidatos de cada tipo de prova."""
        return np.bincount(self.tipo_cand, minlength=NUM_TIPOS)


# ------------------------------------------------------------------------------------- leitura
def ler_instancia(caminho):
    caminho = str(caminho)
    try:
        with open(caminho, encoding="utf-8-sig", errors="replace") as f:
            linhas = [(n, s.strip()) for n, s in enumerate(f, 1) if s.strip()]
    except OSError:
        raise ErroInstancia(f"{caminho}: não foi possível abrir o arquivo")

    def erro(msg, n=None):
        raise ErroInstancia(f"{caminho}:{n}: {msg}" if n else f"{caminho}: {msg}")

    # cabeçalho: tudo antes da primeira seção "#"
    inicio = next((k for k, (_, s) in enumerate(linhas) if s.startswith("#")), len(linhas))
    cab = " ".join(s for _, s in linhas[:inicio])
    contagens = {}
    for rot in ("NUM_CANDIDATOS", "NUM_ESCOLAS"):
        m = re.search(rot + r"\s*:\s*(\d+)", cab)
        if not m:
            erro(f"cabeçalho sem {rot}", linhas[0][0] if linhas else None)
        contagens[rot] = int(m.group(1))
    M, N = contagens["NUM_CANDIDATOS"], contagens["NUM_ESCOLAS"]

    # seções: "# CANDIDATOS", "# ESCOLAS" e "# MATRIZ_DISTANCIAS", cada uma seguida das linhas de dados
    secoes, atual = {}, None
    for n, s in linhas[inicio:]:
        if s.startswith("#"):
            nome = s[1:].strip().upper()
            atual = next((k for k in ("MATRIZ", "CANDIDATOS", "ESCOLAS") if nome.startswith(k)), None)
            if atual is None:
                erro(f"seção desconhecida: {s}", n)
            secoes[atual] = []
        else:
            secoes[atual].append((n, [c.strip() for c in s.split(",")]))
    for sec, qtd in (("CANDIDATOS", M), ("ESCOLAS", N), ("MATRIZ", M)):
        if len(secoes.get(sec, [])) != qtd:
            erro(f"seção {sec} com {len(secoes.get(sec, []))} linhas, esperava {qtd}")

    def numero(conv, s, n):
        try:
            return conv(s)
        except ValueError:
            erro(f"número inválido: '{s}'", n)

    candidatos = []
    for n, c in secoes["CANDIDATOS"]:
        if len(c) != 5:
            erro("candidato deve ter 5 campos (id, CEP, tipo_prova, latitude, longitude)", n)
        if c[2] not in NOMES_TIPOS:
            erro(f"tipo de prova desconhecido: '{c[2]}'", n)
        candidatos.append(Candidato(c[0], c[1].replace("-", ""), NOMES_TIPOS.index(c[2]),
                                    numero(float, c[3], n), numero(float, c[4], n)))

    escolas = []
    for n, c in secoes["ESCOLAS"]:
        if len(c) != 6:
            erro("escola deve ter 6 campos (id, CEP, latitude, longitude, num_salas, capacidades_salas)", n)
        salas = [numero(int, s, n) for s in c[5].split(";")]
        if len(salas) != numero(int, c[4], n):
            erro(f"escola {c[0]} declara {c[4]} salas mas lista {len(salas)}", n)
        if min(salas) <= 0:
            erro(f"escola {c[0]} com sala de capacidade não positiva", n)
        escolas.append(Escola(c[0], c[1].replace("-", ""), numero(float, c[2], n), numero(float, c[3], n), salas))

    D = np.empty((M, N))
    for i, (n, c) in enumerate(secoes["MATRIZ"]):
        if len(c) != N:
            erro(f"linha da matriz com {len(c)} valores, esperava {N}", n)
        D[i] = [numero(float, v, n) for v in c]
    if not np.isfinite(D).all() or (D < 0).any():
        erro("distância inválida na matriz")
    return Instancia(caminho, candidatos, escolas, D)


# ------------------------------------------------------------------------------- conjunto de testes
def listar_instancias(caminhos=PASTAS_PADRAO):
    """Arquivos .txt das pastas/arquivos dados, na ordem dada, sem conteúdo repetido."""
    arqs = []
    for c in map(Path, caminhos):
        arqs += sorted(c.glob("*.txt")) if c.is_dir() else [c]
    vistos, unicos = {}, []
    for a in arqs:
        h = hashlib.md5(a.read_bytes()).hexdigest()
        if h in vistos:
            print(f"(ignorando {rotulo(a)}: igual a {rotulo(vistos[h])})", file=sys.stderr)
            continue
        vistos[h] = a
        unicos.append(a)
    return unicos


def rotulo(arquivo):
    """Nome da instância nos resultados: caminho relativo à raiz do projeto, sem .txt
    (instancias/ e instancias_pism/ têm nomes repetidos)."""
    a = Path(arquivo).resolve()
    try:
        return str(a.relative_to(RAIZ).with_suffix(""))
    except ValueError:
        return a.stem


# ------------------------------------------------------------------------------------- resumo
def resumo(inst):
    dem = inst.demanda()
    folga = 100 * (inst.cap.sum() - inst.M) / inst.M
    return (f"{rotulo(inst.arquivo):40s} M={inst.M:<5d} N={inst.N:<3d} salas={inst.num_salas:<4d} "
            f"cap={inst.cap.sum():<5d} folga={folga:5.1f}%  "
            + " ".join(f"{NOMES_TIPOS[t]}={dem[t]}" for t in range(NUM_TIPOS)))


def main(argv):
    if not argv:
        print(f"Uso: python {sys.argv[0]} <instancia_ou_pasta> [...]", file=sys.stderr)
        return 1
    falhas = 0
    for arq in listar_instancias(argv):
        try:
            print(resumo(ler_instancia(arq)))
        except ErroInstancia as e:
            print(f"ERRO: {e}", file=sys.stderr)
            falhas += 1
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
