"""Heurística construtiva (um tipo de prova por sala, até `max_tipos` tipos por escola, 1 ou 2).

Fase A: tipo de cada sala (determinística).
  A1. Alocação provisória por arrependimento usando só a capacidade da escola (ignora os tipos):
      estima quantos candidatos de cada tipo "querem" cada escola, d[j, t].
  A2. Tipos de cada escola: os max_tipos tipos de maior d[j, t] (só os com d[j, t] > 0).
  A3. Em cada escola, enquanto algum dos seus tipos tem falta (d[j, t] - capacidade já dada a t), o
      de maior falta recebe a menor sala que cobre a falta (best-fit); se nenhuma cobre, a maior.
  A4. Salas que sobraram recebem, entre os tipos da escola (ou qualquer tipo, se a escola ainda
      pode receber mais um), o de maior déficit global (capacidade < demanda); sem déficit, o de
      maior falta local. Abrir uma sala nunca piora a solução.
  A5. Cobertura: enquanto algum tipo t tem capacidade total < demanda, passa para t uma sala de um
      tipo u (se a escola continua com até max_tipos tipos) ou todas as salas de u da escola, desde
      que a sobra de u (capacidade - demanda) cubra as vagas perdidas; entre as candidatas, a da
      escola onde t tem mais falta local (empate: menos vagas mudadas).
  A6. Se A5 trava (nenhuma retipagem simples cobre t sem descobrir outro tipo), reparo exato: um
      modelo pequeno, só com as salas e os tipos (sem candidatos), muda o tipo do menor total de
      vagas possível para cobrir todas as demandas respeitando max_tipos. Se ele não tem solução,
      a instância é inviável e lança ErroConstrucao.
      Ao final, capacidade do tipo t >= demanda do tipo t: é o que impede a fase B de travar.

Fase B: alocação dos candidatos (lista restrita de candidatos, RCL de tamanho k)
  B1. Pré-processamento: cada candidato tem o vetor das escolas ordenado da menor para a maior
      distância.
  B2. Arrependimento estático: distância à 2ª escola mais próxima - distância à 1ª (entre todas
      as escolas). A fila de candidatos é ordenada do maior para o menor arrependimento, uma única
      vez.
  B3. RCL: os k primeiros candidatos ainda não alocados da fila.
  B4. Sorteia um candidato da RCL; percorre o vetor de proximidade dele e o aloca na primeira
      escola que tem uma sala do seu tipo com vaga (salas maiores primeiro).
  B5. A vaga é descontada da sala, o candidato sai da RCL e o próximo da fila entra.
  Com k = 1 a construção é determinística. Nunca trava: pela fase A, a capacidade de cada tipo
  cobre sua demanda, e o vetor de proximidade contém todas as escolas.
"""
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix

from instancia import NOMES_TIPOS, NUM_TIPOS as T
from solucao import Solucao


class ErroConstrucao(Exception):
    pass


def _log(traco, msg):
    if traco is not None:
        traco.write(msg + "\n")


def fase_a(inst, traco=None, max_tipos=1):
    """Tipo de cada sala, com no máximo max_tipos tipos por escola. Devolve (tipo_sala, salas
    retipadas nas etapas A5/A6, se o reparo exato A6 foi usado)."""
    D, N, tc = inst.D, inst.N, inst.tipo_cand
    tipo_sala = [np.full(len(e.salas), -1, dtype=int) for e in inst.escolas]
    capjt = np.zeros((N, T), int)        # capacidade já dada a cada (escola, tipo)
    dem = inst.demanda()
    _log(traco, f"== FASE A: tipo de cada sala (até {max_tipos} tipo(s) por escola)")
    # A1. alocação provisória por arrependimento, só com a capacidade da escola
    ds = np.sort(D, 1)
    reg = ds[:, 1] - ds[:, 0] if N > 1 else np.zeros(inst.M)
    pref = np.argsort(D, 1, kind="stable")
    livre = inst.cap.copy()
    d_esc = np.zeros((N, T), int)        # demanda estimada de cada (escola, tipo)
    for i in np.argsort(-reg, kind="stable"):
        j = next(j for j in pref[i] if livre[j] > 0)
        livre[j] -= 1
        d_esc[j, tc[i]] += 1
    _log(traco, "A1. demanda estimada por escola (alocação provisória sem tipo):")
    for j, e in enumerate(inst.escolas):
        _log(traco, f"    {e.id} (cap {inst.cap[j]}): "
                    + " ".join(f"{NOMES_TIPOS[t]}={d_esc[j, t]}" for t in range(T) if d_esc[j, t]))
    # A2. tipos de cada escola: os max_tipos de maior demanda estimada
    tipos = [[int(t) for t in np.argsort(-d_esc[j], kind="stable")[:max_tipos] if d_esc[j, t] > 0]
             for j in range(N)]
    _log(traco, "A2. tipos de cada escola: " + " ".join(
        f"{e.id}={'+'.join(NOMES_TIPOS[t] for t in tipos[j]) or '-'}" for j, e in enumerate(inst.escolas)))
    # A3. best-fit das salas para cobrir a demanda local dos tipos da escola
    _log(traco, "A3. salas para os tipos (best-fit):")
    for j, e in enumerate(inst.escolas):
        salas = sorted(range(len(e.salas)), key=lambda r: e.salas[r])
        while salas and tipos[j]:
            falta = d_esc[j] - capjt[j]
            t = max(tipos[j], key=lambda t: falta[t])
            if falta[t] <= 0:
                break
            cabe = [r for r in salas if e.salas[r] >= falta[t]]
            r = cabe[0] if cabe else salas[-1]
            salas.remove(r)
            tipo_sala[j][r] = t
            capjt[j, t] += e.salas[r]
            _log(traco, f"    {e.id} sala {r + 1} ({e.salas[r]}) -> {NOMES_TIPOS[t]} (falta {falta[t]})")
    # A4. salas que sobraram: o tipo com maior déficit global (capacidade < demanda) entre os da
    # escola, ou um tipo novo se a escola ainda pode receber; sem déficit, o de maior falta local
    for j, e in enumerate(inst.escolas):
        for r in sorted(np.flatnonzero(tipo_sala[j] < 0), key=lambda r: -e.salas[r]):
            deficit = dem - capjt.sum(0)
            pode = tipos[j] if len(tipos[j]) == max_tipos else range(T)
            t = max(pode, key=lambda t: (deficit[t] > 0, deficit[t] if deficit[t] > 0 else d_esc[j, t] - capjt[j, t]))
            if t not in tipos[j]:
                tipos[j].append(t)
            tipo_sala[j][r] = t
            capjt[j, t] += e.salas[r]
            _log(traco, f"A4. {e.id} sala {r + 1} ({e.salas[r]}) sobrou -> {NOMES_TIPOS[t]}")
    # A5. cobertura: capacidade de cada tipo >= demanda
    retip, reparo = 0, False
    while True:
        deficit = dem - capjt.sum(0)
        t = int(deficit.argmax())
        if deficit[t] <= 0:
            break
        melhor = None
        for j in range(N):
            falta_t = d_esc[j, t] - capjt[j, t]
            for u in set(tipo_sala[j]) - {t}:
                rs = np.flatnonzero(tipo_sala[j] == u)
                # uma sala de u (se a escola continua com até max_tipos tipos) ou todas as salas de u
                restam = len(set(tipo_sala[j]) | {t}) - (len(rs) == 1)
                movs = [[r] for r in rs] if restam <= max_tipos else []
                if len(rs) > 1:
                    movs.append(list(rs))
                for R in movs:
                    q = int(sum(inst.escolas[j].salas[r] for r in R))
                    if -deficit[u] >= q:
                        chave = (-falta_t, q)
                        if melhor is None or chave < melhor[0]:
                            melhor = (chave, j, u, R, q)
        if melhor is None:
            _log(traco, f"A5. {NOMES_TIPOS[t]} sem cobertura (falta {deficit[t]}) e nenhuma retipagem "
                        f"simples resolve: reparo exato")
            mudou = _reparar(inst, tipo_sala, max_tipos)
            if mudou is None:
                raise ErroConstrucao(f"não há como cobrir a demanda de todos os tipos com até {max_tipos} "
                                     f"tipo(s) por escola (instância inviável)")
            for j, r, u, v in mudou:
                _log(traco, f"A6. {inst.escolas[j].id} sala {r + 1} ({inst.escolas[j].salas[r]}) "
                            f"{NOMES_TIPOS[u]} -> {NOMES_TIPOS[v]}")
                capjt[j, u] -= inst.escolas[j].salas[r]
                capjt[j, v] += inst.escolas[j].salas[r]
            retip += len(mudou)
            reparo = True
            break
        _, j, u, R, q = melhor
        tipo_sala[j][R] = t
        capjt[j, u] -= q
        capjt[j, t] += q
        retip += len(R)
        _log(traco, f"A5. {NOMES_TIPOS[t]} sem cobertura (falta {deficit[t]}): {inst.escolas[j].id} sala(s) "
                    f"{','.join(str(r + 1) for r in R)} ({q} vagas) {NOMES_TIPOS[u]} -> {NOMES_TIPOS[t]}")
    _log(traco, "capacidade por tipo: " + " ".join(
        f"{NOMES_TIPOS[t]}={capjt[:, t].sum()}/{dem[t]}" for t in range(T)))
    return tipo_sala, retip, reparo


def _reparar(inst, tipo_sala, max_tipos):
    """A6. Reparo exato da cobertura: muda o tipo do menor total de vagas possível para que cada tipo
    tenha capacidade >= demanda, com no máximo max_tipos tipos por escola. Modelo pequeno (sem
    distâncias) resolvido pelo HiGHS: x[r, t] = sala r recebe t, y[j, t] = escola j oferece t.
    Altera tipo_sala e devolve [(j, r, tipo antigo, tipo novo)], ou None se não há solução."""
    salas = [(j, r, c) for j, e in enumerate(inst.escolas) for r, c in enumerate(e.salas)]
    S, N = len(salas), inst.N
    x = lambda k, t: k * T + t
    y = lambda j, t: S * T + j * T + t
    nv = S * T + N * T
    custo = np.zeros(nv)
    lin, col, val, lo, hi = [], [], [], [], []

    def restr(coef, a, b):
        for c, v in coef.items():
            lin.append(len(lo))
            col.append(c)
            val.append(v)
        lo.append(a)
        hi.append(b)

    for k, (j, r, c) in enumerate(salas):
        for t in range(T):
            custo[x(k, t)] = c * (t != tipo_sala[j][r])
            restr({x(k, t): 1, y(j, t): -1}, -np.inf, 0)               # sala só com tipo da escola
        restr({x(k, t): 1 for t in range(T)}, 1, 1)                     # um tipo por sala
    for j in range(N):
        restr({y(j, t): 1 for t in range(T)}, 0, max_tipos)            # até max_tipos por escola
    dem = inst.demanda()
    for t in range(T):
        restr({x(k, t): c for k, (_, _, c) in enumerate(salas)}, dem[t], np.inf)
    A = csr_matrix((val, (lin, col)), shape=(len(lo), nv))
    res = milp(custo, constraints=LinearConstraint(A, lo, hi), integrality=np.ones(nv),
               bounds=Bounds(0, 1), options={"time_limit": 30})
    if res.x is None:
        return None
    mudou = []
    for k, (j, r, _) in enumerate(salas):
        v = int(np.argmax(res.x[x(k, 0):x(k, 0) + T]))
        if v != tipo_sala[j][r]:
            mudou.append((j, r, int(tipo_sala[j][r]), v))
            tipo_sala[j][r] = v
    return mudou


def fase_b(inst, tipo_sala, k=1, rng=None, traco=None):
    """Alocação por arrependimento estático com RCL de tamanho k. Devolve (aloc, sala)."""
    D, M, N, tc = inst.D, inst.M, inst.N, inst.tipo_cand
    # B1. vetor de proximidade de cada candidato
    pref = np.argsort(D, axis=1, kind="stable")
    # B2. arrependimento estático (2ª - 1ª escola mais próxima) e fila ordenada, uma única vez
    d12 = np.take_along_axis(D, pref[:, :2], 1) if N > 1 else np.zeros((M, 2))
    reg = d12[:, 1] - d12[:, 0]
    fila = np.argsort(-reg, kind="stable")
    # vagas por sala; salas de cada (escola, tipo), maiores primeiro
    vaga = [np.array(e.salas) for e in inst.escolas]
    salas_jt = {}
    vaga_jt = np.zeros((N, T), int)
    for j, e in enumerate(inst.escolas):
        for r in sorted(range(len(e.salas)), key=lambda r: -e.salas[r]):
            t = tipo_sala[j][r]
            if t >= 0:
                salas_jt.setdefault((j, t), []).append(r)
                vaga_jt[j, t] += e.salas[r]
    aloc = np.full(M, -1)
    sala = np.full(M, -1)
    rcl = list(fila[:k])
    prox = len(rcl)
    _log(traco, f"== FASE B: alocação com RCL de tamanho k={k}")
    passo = 0
    while rcl:
        passo += 1
        p = int(rng.integers(len(rcl))) if len(rcl) > 1 else 0
        if traco is not None:
            desc = ", ".join(f"{inst.candidatos[c].id}({reg[c]:.3f})" for c in rcl)
        i = rcl.pop(p)
        t = tc[i]
        pulos = []
        for j in pref[i]:
            if vaga_jt[j, t] > 0:
                break
            if traco is not None:
                pulos.append(f"{inst.escolas[j].id}:{'lotada' if (j, t) in salas_jt else 'sem sala'}")
        else:
            raise ErroConstrucao(f"candidato {inst.candidatos[i].id} sem sala do tipo {NOMES_TIPOS[t]}")
        r = next(r for r in salas_jt[j, t] if vaga[j][r] > 0)
        vaga[j][r] -= 1
        vaga_jt[j, t] -= 1
        aloc[i], sala[i] = j, r
        if prox < M:
            rcl.append(fila[prox])
            prox += 1
        if traco is not None:
            _log(traco, f"{passo:5d} RCL=[{desc}] sorteado {inst.candidatos[i].id} ({NOMES_TIPOS[t]}) -> "
                        f"{inst.escolas[j].id} sala {r + 1} d={D[i, j]:.4f}"
                        + (f"  [pulou {' '.join(pulos)}]" if pulos else ""))
    return aloc, sala


def construir(inst, k=1, rng=None, traco=None, max_tipos=1):
    """Solução inicial viável com até max_tipos tipos de prova por escola. Devolve (Solucao, info)."""
    t0 = time.perf_counter()
    tipo_sala, retip, reparo = fase_a(inst, traco, max_tipos)
    t1 = time.perf_counter()
    aloc, _ = fase_b(inst, tipo_sala, k, rng, traco)
    t2 = time.perf_counter()
    sol = Solucao(inst, tipo_sala, aloc, max_tipos)
    _log(traco, f"solução inicial: custo {sol.custo:.4f}")
    return sol, {"t_fase_a": t1 - t0, "t_fase_b": t2 - t1, "retipagens": retip, "reparo": int(reparo)}
