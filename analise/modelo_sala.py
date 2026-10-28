"""Referências do modelo adotado (um tipo de prova por sala), usadas para medir a heurística.

Para cada instância:
  viavel      as salas podem ser repartidas entre os tipos com capacidade >= demanda de cada tipo?
              (guloso; se falhar, decide por um MIP de viabilidade)
  LB          limite inferior: transporte em que cada escola aceita qualquer tipo até a sua
              capacidade Q_j. É a relaxação linear do MIP abaixo.
  MIP         y[j,c,t] = nº de salas de capacidade c da escola j que recebem o tipo t (inteiro; salas
              iguais agregadas para eliminar simetria), x[g,j] contínuo (g = grupo de candidatos
              idênticos). Resolvido pelo HiGHS com limite de tempo: melhor solução, limite inferior
              e se o ótimo foi provado.
  aloc_otima  alocação ótima (transporte) com os tipos de sala da fase A do construtivo: o valor
              que N1-N3 alcançariam sem mudar tipos.

Grava analise/resultados/modelo_sala.csv.
Uso: .venv/bin/python analise/modelo_sala.py [limite_s_mip]   (padrão 60 s)
"""
import csv
import sys
import time

import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog

from comum import SAIDA, T, grupos, instancias, resolver_mip, salas_agregadas, transporte
from construtivo import ErroConstrucao, fase_a


def viavel(inst):
    """Existe uma atribuição de tipos às salas que cubra a demanda de cada tipo?"""
    falta = inst.demanda().astype(float)
    for c in sorted((c for e in inst.escolas for c in e.salas), reverse=True):
        t = falta.argmax()
        if falta[t] <= 0:
            break
        falta[t] -= c
    if (falta <= 0).all():
        return True
    # o guloso falhou: MIP de viabilidade (w[k,t] = salas da classe k que recebem o tipo t)
    ag, dem = salas_agregadas(inst), inst.demanda()
    nv = len(ag) * T
    linhas = [({k * T + t: c for k, (_, c, _) in enumerate(ag)}, dem[t], np.inf) for t in range(T)]
    linhas += [({k * T + t: 1 for t in range(T)}, 0, n) for k, (_, _, n) in enumerate(ag)]
    return resolver_mip(np.zeros(nv), linhas, np.ones(nv), np.inf, 30)[3] is not None


def limite_inferior(inst):
    """Transporte em que a capacidade Q_j da escola é compartilhada livremente entre os tipos."""
    _, cnt, Dg = grupos(inst)
    G, N = len(cnt), inst.N
    A_eq = sp.kron(sp.eye(G), np.ones((1, N)), format="csr")     # cada grupo alocado
    A_ub = sp.kron(np.ones((1, G)), sp.eye(N), format="csr")     # capacidade da escola
    r = linprog(Dg.ravel(), A_ub=A_ub, b_ub=inst.cap, A_eq=A_eq, b_eq=cnt, method="highs")
    return r.fun


def mip(inst, limite):
    tg, cnt, Dg = grupos(inst)
    G, N = len(tg), inst.N
    ag = salas_agregadas(inst)
    nx = G * N
    c = np.concatenate([Dg.ravel(), np.zeros(len(ag) * T)])
    linhas = [({g * N + j: 1 for j in range(N)}, cnt[g], cnt[g]) for g in range(G)]   # grupo alocado
    # capacidade de (j, t): candidatos do tipo t em j <= soma das salas de j com tipo t
    cap = {(j, t): {} for j in range(N) for t in range(T)}
    for g in range(G):
        for j in range(N):
            cap[j, tg[g]][g * N + j] = 1
    for k, (j, c_sala, _) in enumerate(ag):
        for t in range(T):
            cap[j, t][nx + k * T + t] = -c_sala
    linhas += [(coef, -np.inf, 0) for coef in cap.values()]
    linhas += [({nx + k * T + t: 1 for t in range(T)}, 0, n) for k, (_, _, n) in enumerate(ag)]  # 1 tipo/sala
    integ = np.concatenate([np.zeros(nx), np.ones(len(ag) * T)])
    sup = np.concatenate([np.repeat(cnt, N), np.repeat([n for _, _, n in ag], T)])
    melhor, lb, otimo, _ = resolver_mip(c, linhas, integ, sup, limite)
    return melhor, lb, otimo


def aloc_otima_construtivo(inst):
    try:
        tipo_sala, _ = fase_a(inst)
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
        r = {"instancia": nome, "viavel": int(viavel(inst))}
        if r["viavel"]:
            t0 = time.time()
            r["LB"] = limite_inferior(inst)
            r["MIP"], r["MIP_lb"], ot = mip(inst, limite)
            r["MIP_otimo"] = int(ot)
            r["t_mip"] = round(time.time() - t0, 1)
            r["aloc_otima"] = aloc_otima_construtivo(inst)
            print(f"{nome:40s} LB={r['LB']:12.2f} MIP={r['MIP'] or float('nan'):12.2f}{'*' if ot else ' '} "
                  f"aloc_otima={r['aloc_otima'] or float('nan'):12.2f}  t_mip={r['t_mip']}s", flush=True)
        else:
            print(f"{nome:40s} INVIÁVEL: as salas não cobrem a demanda de todos os tipos", flush=True)
        linhas.append(r)
    with open(SAIDA / "modelo_sala.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["instancia", "viavel", "LB", "MIP", "MIP_lb", "MIP_otimo", "t_mip", "aloc_otima"])
        w.writeheader()
        w.writerows(linhas)


if __name__ == "__main__":
    main()
