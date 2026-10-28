"""Funções compartilhadas pelas análises: lista de instâncias (a mesma dos experimentos),
agrupamento de candidatos idênticos, alocação ótima por PL de transporte e chamada ao MIP."""
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.optimize import Bounds, LinearConstraint, linprog, milp

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from instancia import (NOMES_TIPOS as TIPOS, NUM_TIPOS as T, ErroInstancia,  # noqa: E402,F401
                       ler_instancia, listar_instancias, rotulo)

SAIDA = Path(__file__).resolve().parent / "resultados"


def instancias():
    """(rótulo, Instancia) de instancias/ e instancias_pism/, sem conteúdo repetido."""
    for arq in listar_instancias():
        try:
            yield rotulo(arq), ler_instancia(arq)
        except ErroInstancia as e:
            print(f"ERRO: {e}", file=sys.stderr)


def grupos(inst):
    """Agrupa candidatos com o mesmo tipo e a mesma linha de distâncias (reduz os modelos).
    Devolve (tipo_g, quantidade_g, D_g)."""
    chave = np.column_stack([inst.tipo_cand, np.round(inst.D, 6)])
    _, rep, cnt = np.unique(chave, axis=0, return_index=True, return_counts=True)
    return inst.tipo_cand[rep], cnt, inst.D[rep]


def salas_agregadas(inst):
    """Salas iguais da mesma escola agregadas: lista de (escola j, capacidade c, quantidade n)."""
    return [(j, c, n) for j, e in enumerate(inst.escolas) for c, n in sorted(Counter(e.salas).items())]


def transporte(inst, capjt):
    """Custo da alocação ótima com capacidade capjt[j, t] por (escola, tipo), resolvida como
    problema de transporte (PL). None se não houver alocação viável."""
    tg, cnt, Dg = grupos(inst)
    gg, jj = np.nonzero(capjt[:, tg].T > 0)          # arcos (grupo, escola) permitidos
    if len(gg) == 0:
        return None
    arco = np.arange(len(gg))
    A_eq = sp.csr_matrix((np.ones(len(gg)), (gg, arco)), shape=(len(tg), len(gg)))
    A_ub = sp.csr_matrix((np.ones(len(gg)), (jj * T + tg[gg], arco)), shape=(inst.N * T, len(gg)))
    r = linprog(Dg[gg, jj], A_ub=A_ub, b_ub=capjt.ravel(), A_eq=A_eq, b_eq=cnt, method="highs")
    return r.fun if r.status == 0 else None


def resolver_mip(c, linhas, integ, sup, limite):
    """MIP min c x s.a. lo <= A x <= hi, 0 <= x <= sup. `linhas` é uma lista de
    (coeficientes {coluna: valor}, lo, hi). Devolve (melhor valor, limite inferior, ótimo provado, x)."""
    lin, col, val, lo, hi = [], [], [], [], []
    for r, (coef, a, b) in enumerate(linhas):
        lin += [r] * len(coef)
        col += list(coef)
        val += list(coef.values())
        lo.append(a)
        hi.append(b)
    A = sp.csr_matrix((val, (lin, col)), shape=(len(linhas), len(c)))
    res = milp(c, constraints=LinearConstraint(A, lo, hi), integrality=integ, bounds=Bounds(0, sup),
               options={"time_limit": limite, "disp": False, "mip_rel_gap": 1e-6})
    melhor = res.fun if res.x is not None else None
    return melhor, getattr(res, "mip_dual_bound", None), res.status == 0, res.x
