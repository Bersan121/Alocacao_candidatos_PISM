"""Referências exatas do modelo adotado (um tipo de prova por sala, no máximo K tipos por escola,
K = 1 ou 2), usadas para medir a heurística.

Para cada instância:
  LB            limite inferior: transporte em que cada escola aceita qualquer tipo até a sua
                capacidade Q_j. Vale para K = 1 e K = 2 (é a relaxação dos dois MIPs).
E, para cada K (colunas com sufixo 1 e 2):
  viavel        as salas podem receber tipos, com até K por escola, de forma que a capacidade de
                cada tipo cubra a sua demanda? (MIP de viabilidade, sem candidatos)
  MIP           y[j,t] = escola j oferece t (binário, sum_t y[j,t] <= K); w[k,t] = nº de salas da
                classe k (salas iguais da mesma escola) que recebem t, w[k,t] <= n_k y[j,t];
                x[g,j] contínuo (g = grupo de candidatos idênticos), com os cortes
                x[g,j] <= n_g y[j,t_g]. Com K = 1 as salas da escola têm todas o tipo da escola e o
                modelo usa só y[j,t], com capacidade Q_j y[j,t]. Resolvido pelo HiGHS com limite de
                tempo: melhor solução, limite inferior e se o ótimo foi provado.
  aloc_otima    alocação ótima (transporte) com os tipos de sala da fase A do construtivo: o valor
                que N1-N3 alcançariam sem mudar tipos.

Grava analise/resultados/modelo_exato.csv.
Uso: .venv/bin/python analise/modelo_exato.py [limite_s_mip]   (padrão 60 s por MIP)
"""
import csv
import sys
import time

import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog

from comum import SAIDA, T, grupos, instancias, resolver_mip, salas_agregadas, transporte
from construtivo import ErroConstrucao, fase_a

KS = (1, 2)


def limite_inferior(inst):
    """Transporte em que a capacidade Q_j da escola é compartilhada livremente entre os tipos."""
    _, cnt, Dg = grupos(inst)
    G, N = len(cnt), inst.N
    A_eq = sp.kron(sp.eye(G), np.ones((1, N)), format="csr")     # cada grupo alocado
    A_ub = sp.kron(np.ones((1, G)), sp.eye(N), format="csr")     # capacidade da escola
    r = linprog(Dg.ravel(), A_ub=A_ub, b_ub=inst.cap, A_eq=A_eq, b_eq=cnt, method="highs")
    return r.fun


def restricoes_tipos(inst, K, n0):
    """Restrições das variáveis de tipo a partir da coluna n0: w[k,t] (salas da classe k com o
    tipo t) e y[j,t]. Devolve (linhas, ag, w, y, nº de variáveis)."""
    ag, dem, N = salas_agregadas(inst), inst.demanda(), inst.N
    w = lambda k, t: n0 + k * T + t
    y = lambda j, t: n0 + len(ag) * T + j * T + t
    linhas = [({w(k, t): c for k, (_, c, _) in enumerate(ag)}, dem[t], np.inf) for t in range(T)]   # cobertura
    linhas += [({w(k, t): 1 for t in range(T)}, 0, n) for k, (_, _, n) in enumerate(ag)]           # salas da classe
    linhas += [({w(k, t): 1, y(j, t): -n}, -np.inf, 0) for k, (j, _, n) in enumerate(ag) for t in range(T)]
    linhas += [({y(j, t): 1 for t in range(T)}, 0, K) for j in range(N)]                           # até K tipos
    return linhas, ag, w, y, len(ag) * T + N * T


def viavel(inst, K):
    linhas, ag, *_, nv = restricoes_tipos(inst, K, 0)
    sup = np.concatenate([np.repeat([n for *_, n in ag], T), np.ones(inst.N * T)])
    return resolver_mip(np.zeros(nv), linhas, np.ones(nv), sup, 30)[3] is not None


def mip(inst, K, limite):
    if K == 1:
        return mip_escola(inst, limite)
    tg, cnt, Dg = grupos(inst)
    G, N = len(tg), inst.N
    nx = G * N
    linhas, ag, w, y, nt = restricoes_tipos(inst, K, nx)
    c = np.concatenate([Dg.ravel(), np.zeros(nt)])
    linhas += [({g * N + j: 1 for j in range(N)}, cnt[g], cnt[g]) for g in range(G)]      # grupo alocado
    # capacidade de (j, t): candidatos do tipo t em j <= soma das salas de j com tipo t
    cap = {(j, t): {} for j in range(N) for t in range(T)}
    for g in range(G):
        for j in range(N):
            cap[j, tg[g]][g * N + j] = 1
    for k, (j, c_sala, _) in enumerate(ag):
        for t in range(T):
            cap[j, t][w(k, t)] = -c_sala
    linhas += [(coef, -np.inf, 0) for coef in cap.values()]
    linhas += [({g * N + j: 1, y(j, tg[g]): -cnt[g]}, -np.inf, 0) for g in range(G) for j in range(N)]
    integ = np.concatenate([np.zeros(nx), np.ones(nt)])
    sup = np.concatenate([np.repeat(cnt, N), np.repeat([n for *_, n in ag], T), np.ones(N * T)])
    melhor, lb, otimo, _ = resolver_mip(c, linhas, integ, sup, limite)
    return melhor, lb, otimo


def mip_escola(inst, limite):
    """K = 1: todas as salas da escola têm o mesmo tipo, então basta y[j,t] e a capacidade da
    escola vira Q_j y[j,t] (formulação mais compacta, sem as variáveis de sala)."""
    tg, cnt, Dg = grupos(inst)
    G, N, dem = len(tg), inst.N, inst.demanda()
    nx = G * N
    y = lambda j, t: nx + j * T + t
    c = np.concatenate([Dg.ravel(), np.zeros(N * T)])
    linhas = [({g * N + j: 1 for j in range(N)}, cnt[g], cnt[g]) for g in range(G)]       # grupo alocado
    for j in range(N):                                                                  # capacidade
        for t in range(T):
            coef = {g * N + j: 1 for g in np.flatnonzero(tg == t)}
            coef[y(j, t)] = -inst.cap[j]
            linhas.append((coef, -np.inf, 0))
    linhas += [({y(j, t): 1 for t in range(T)}, 0, 1) for j in range(N)]                # um tipo por escola
    linhas += [({y(j, t): inst.cap[j] for j in range(N)}, dem[t], np.inf) for t in range(T)]   # cobertura
    linhas += [({g * N + j: 1, y(j, tg[g]): -cnt[g]}, -np.inf, 0) for g in range(G) for j in range(N)]
    integ = np.concatenate([np.zeros(nx), np.ones(N * T)])
    sup = np.concatenate([np.repeat(cnt, N), np.ones(N * T)])
    melhor, lb, otimo, _ = resolver_mip(c, linhas, integ, sup, limite)
    return melhor, lb, otimo


def aloc_otima_construtivo(inst, K):
    try:
        tipo_sala, _, _ = fase_a(inst, max_tipos=K)
    except ErroConstrucao:
        return None
    capjt = np.zeros((inst.N, T), int)
    for j, e in enumerate(inst.escolas):
        np.add.at(capjt[j], tipo_sala[j], e.salas)
    return transporte(inst, capjt)


def main():
    limite = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    SAIDA.mkdir(exist_ok=True)
    linhas = []
    for nome, inst in instancias():
        r = {"instancia": nome, "LB": limite_inferior(inst)}
        msg = f"{nome:36s} LB={r['LB']:12.2f}"
        for K in KS:
            r[f"viavel{K}"] = int(viavel(inst, K))
            if r[f"viavel{K}"]:
                t0 = time.time()
                r[f"MIP{K}"], r[f"MIP_lb{K}"], ot = mip(inst, K, limite)
                r[f"MIP_otimo{K}"] = int(ot)
                r[f"t_mip{K}"] = round(time.time() - t0, 1)
                r[f"aloc_otima{K}"] = aloc_otima_construtivo(inst, K)
                msg += (f" | K={K}: MIP={r[f'MIP{K}'] or float('nan'):12.2f}{'*' if ot else ' '} "
                        f"aloc_otima={r[f'aloc_otima{K}'] or float('nan'):12.2f} t={r[f't_mip{K}']}s")
            else:
                msg += f" | K={K}: INVIÁVEL"
        print(msg, flush=True)
        linhas.append(r)
    with open(SAIDA / "modelo_exato.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["instancia", "LB"] + [f"{c}{K}" for K in KS for c in
                                                     ("viavel", "MIP", "MIP_lb", "MIP_otimo", "t_mip", "aloc_otima")])
        w.writeheader()
        w.writerows(linhas)


if __name__ == "__main__":
    main()
