"""Interpretação alternativa: cada ESCOLA oferece um único tipo de prova. Serve para comparar com o
modelo adotado (um tipo por sala), na Seção "Comparação com a interpretação um tipo por escola" do
relatório.

Para cada instância:
  viavel      existe uma escolha de tipos das escolas que cubra a demanda de cada tipo?
              (cobertura de bins, resolvida por backtracking)
  MIP         y[j,t] = escola j oferece t, x[g,j] contínuo, com os cortes x[g,j] <= n_g y[j,t_g];
              HiGHS com limite de tempo.
  heuristica  tipos por cobertura gulosa (o par (escola, tipo) cujos candidatos descobertos mais
              próximos estão mais perto, desde que as escolas restantes ainda cubram as faltas),
              alocação ótima por transporte e busca local nos tipos (mudar o tipo de uma escola ou
              trocar os tipos de duas escolas; cada vizinho avaliado por transporte; first improvement).
  melhor      menor valor entre MIP e heurística.

Grava analise/resultados/modelo_escola.csv.
Uso: .venv/bin/python analise/modelo_escola.py [limite_s_mip]   (padrão 60 s)
"""
import csv
import sys
import time

import numpy as np

from comum import SAIDA, T, grupos, instancias, resolver_mip, transporte

LIMITE_BUSCA_S = 120


def capacidade(inst, tipo):
    """Capacidade por (escola, tipo) quando a escola j oferece só o tipo tipo[j] (-1 = fechada)."""
    capjt = np.zeros((inst.N, T), int)
    abertas = np.flatnonzero(tipo >= 0)
    capjt[abertas, tipo[abertas]] = inst.cap[abertas]
    return capjt


def cobre(caps, falta):
    """As escolas com capacidades `caps` podem receber tipos de forma que cada tipo t tenha
    capacidade >= falta[t]? Backtracking (maior escola primeiro) com poda pela capacidade restante
    e memorização de (escola, faltas ordenadas): os tipos são simétricos."""
    caps = sorted(caps, reverse=True)
    resto = np.concatenate([np.cumsum(caps[::-1])[::-1], [0]])
    memo = {}

    def bt(k, falta):
        if not falta:
            return True
        if k == len(caps) or sum(falta) > resto[k]:
            return False
        if (k, falta) not in memo:
            # a escola k cobre um dos tipos (faltas iguais são equivalentes) ou fica sem tipo
            memo[k, falta] = any(
                bt(k + 1, tuple(sorted([f for u, f in enumerate(falta) if u != t]
                                       + ([falta[t] - caps[k]] if falta[t] > caps[k] else []), reverse=True)))
                for t in range(len(falta)) if t == 0 or falta[t] != falta[t - 1]) or bt(k + 1, falta)
        return memo[k, falta]
    return bt(0, tuple(sorted((int(f) for f in falta if f > 0), reverse=True)))


def mip(inst, limite):
    tg, cnt, Dg = grupos(inst)
    G, N = len(tg), inst.N
    nx = G * N
    y = lambda j, t: nx + j * T + t
    c = np.concatenate([Dg.ravel(), np.zeros(N * T)])
    linhas = [({g * N + j: 1 for j in range(N)}, cnt[g], cnt[g]) for g in range(G)]       # grupo alocado
    for j in range(N):                                                                   # capacidade
        for t in range(T):
            coef = {g * N + j: 1 for g in np.flatnonzero(tg == t)}
            coef[y(j, t)] = -inst.cap[j]
            linhas.append((coef, -np.inf, 0))
    linhas += [({y(j, t): 1 for t in range(T)}, 0, 1) for j in range(N)]                 # um tipo por escola
    linhas += [({g * N + j: 1, y(j, tg[g]): -cnt[g]}, -np.inf, 0) for g in range(G) for j in range(N)]
    integ = np.concatenate([np.zeros(nx), np.ones(N * T)])
    sup = np.concatenate([np.repeat(cnt, N), np.ones(N * T)])
    melhor, lb, otimo, _ = resolver_mip(c, linhas, integ, sup, limite)
    return melhor, lb, otimo


def tipos_gulosos(inst):
    """Tipo de cada escola por cobertura gulosa com verificação de viabilidade."""
    D, cap, tc = inst.D, inst.cap, inst.tipo_cand
    tipo = np.full(inst.N, -1)
    falta = inst.demanda().astype(int)
    coberto = np.zeros(inst.M, bool)
    livres = set(range(inst.N))
    while (falta > 0).any():
        pares = []                       # (distância média dos candidatos cobertos, escola, tipo, cobertos)
        for t in np.flatnonzero(falta > 0):
            idx = np.flatnonzero((tc == t) & ~coberto)
            for j in livres:
                k = min(cap[j], falta[t], len(idx))
                d = D[idx, j]
                sel = np.argpartition(d, k - 1)[:k] if k < len(d) else np.arange(len(d))
                pares.append((d[sel].mean(), j, t, idx[sel]))
        pares.sort(key=lambda p: p[0])
        for _, j, t, cob in pares:
            f2 = falta.copy()
            f2[t] -= cap[j]
            if cobre([cap[l] for l in livres if l != j], f2):
                break
        tipo[j] = t
        coberto[cob] = True
        falta[t] -= cap[j]
        livres.remove(j)
    # escolas que sobraram: abrir nunca piora; recebem o tipo de maior ganho estimado
    for j in sorted(livres, key=lambda l: -cap[l]):
        dcur = np.where(tipo[None, :] == tc[:, None], D, np.inf).min(1)
        ganho = np.maximum(0, dcur - D[:, j])
        tipo[j] = int(np.argmax([np.sort(ganho[tc == t])[::-1][:cap[j]].sum() for t in range(T)]))
    return tipo


def busca_tipos(inst, tipo, valor):
    """Muda o tipo de uma escola ou troca os tipos de duas; first improvement."""
    dem, N, t0 = inst.demanda(), inst.N, time.time()
    melhorou = True
    while melhorou and time.time() - t0 < LIMITE_BUSCA_S:
        melhorou = False
        vizinhos = [(j, t) for j in range(N) for t in range(T) if t != tipo[j]]
        vizinhos += [(j, -(k + 1)) for j in range(N) for k in range(j + 1, N) if tipo[j] != tipo[k]]
        for j, m in vizinhos:
            tp = tipo.copy()
            if m >= 0:
                tp[j] = m
            else:
                tp[j], tp[-m - 1] = tp[-m - 1], tp[j]
            if (capacidade(inst, tp).sum(0) < dem).any():
                continue
            v = transporte(inst, capacidade(inst, tp))
            if v is not None and v < valor - 1e-6:
                tipo, valor, melhorou = tp, v, True
                break
            if time.time() - t0 > LIMITE_BUSCA_S:
                break
    return valor


def main():
    limite = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    SAIDA.mkdir(exist_ok=True)
    linhas = []
    for nome, inst in instancias():
        r = {"instancia": nome, "viavel": int(cobre(list(inst.cap), list(inst.demanda())))}
        if r["viavel"]:
            t0 = time.time()
            r["MIP"], r["MIP_lb"], ot = mip(inst, limite)
            r["MIP_otimo"] = int(ot)
            t1 = time.time()
            tipo = tipos_gulosos(inst)
            r["heuristica"] = busca_tipos(inst, tipo, transporte(inst, capacidade(inst, tipo)))
            r["melhor"] = min(v for v in (r["MIP"], r["heuristica"]) if v is not None)
            r["t_mip"], r["t_heuristica"] = round(t1 - t0, 1), round(time.time() - t1, 1)
            print(f"{nome:40s} MIP={r['MIP'] or float('nan'):12.2f}{'*' if ot else ' '} "
                  f"heuristica={r['heuristica']:12.2f}  t={r['t_mip']}+{r['t_heuristica']}s", flush=True)
        else:
            print(f"{nome:40s} INVIÁVEL com um tipo por escola", flush=True)
        linhas.append(r)
    with open(SAIDA / "modelo_escola.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["instancia", "viavel", "MIP", "MIP_lb", "MIP_otimo", "heuristica", "melhor",
                               "t_mip", "t_heuristica"])
        w.writeheader()
        w.writerows(linhas)


if __name__ == "__main__":
    main()
