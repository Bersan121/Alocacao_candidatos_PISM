"""Heurística construtiva (um tipo de prova por sala).

Fase A: tipo de cada sala (determinística).
  A1. Alocação provisória por arrependimento usando só a capacidade da escola (ignora o tipo das
      salas): estima quantos candidatos de cada tipo "querem" cada escola, d[j, t].
  A2. Em cada escola, enquanto algum tipo tem falta (d[j, t] - capacidade já dada a t), o tipo de
      maior falta recebe a menor sala que cobre a falta (best-fit); se nenhuma cobre, a maior.
  A3. Salas que sobraram recebem o tipo com maior déficit global (capacidade < demanda); sem
      déficit, o tipo com maior falta local. Abrir uma sala nunca piora a solução.
  A4. Cobertura: enquanto algum tipo t tem capacidade total < demanda, uma sala de um tipo u cuja
      sobra (capacidade - demanda de u) é >= capacidade da sala passa para t; entre as candidatas,
      a da escola onde t tem mais falta local (empate: a menor sala).
      É o que impede a fase B de travar: ao final, capacidade do tipo t >= demanda do tipo t.
      Se nenhuma sala pode mudar de tipo, lança ErroConstrucao (a instância é inviável; ver
      analise/modelo_sala.py, que confirma com um modelo exato).

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

from instancia import NOMES_TIPOS, NUM_TIPOS as T
from solucao import Solucao


class ErroConstrucao(Exception):
    pass


def _log(traco, msg):
    if traco is not None:
        traco.write(msg + "\n")


def fase_a(inst, traco=None):
    """Tipo de cada sala. Devolve (tipo_sala, retipagens da etapa A4)."""
    D, N, tc = inst.D, inst.N, inst.tipo_cand
    tipo_sala = [np.full(len(e.salas), -1, dtype=int) for e in inst.escolas]
    capjt = np.zeros((N, T), int)        # capacidade já dada a cada (escola, tipo)
    dem = inst.demanda()
    _log(traco, "== FASE A: tipo de cada sala")
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
    # A2. best-fit das salas para cobrir a demanda local
    _log(traco, "A2. salas para os tipos (best-fit):")
    for j, e in enumerate(inst.escolas):
        salas = sorted(range(len(e.salas)), key=lambda r: e.salas[r])
        while salas:
            falta = d_esc[j] - capjt[j]
            t = int(falta.argmax())
            if falta[t] <= 0:
                break
            cabe = [r for r in salas if e.salas[r] >= falta[t]]
            r = cabe[0] if cabe else salas[-1]
            salas.remove(r)
            tipo_sala[j][r] = t
            capjt[j, t] += e.salas[r]
            _log(traco, f"    {e.id} sala {r + 1} ({e.salas[r]}) -> {NOMES_TIPOS[t]} (falta {falta[t]})")
    # A3. salas que sobraram
    for j, e in enumerate(inst.escolas):
        for r in sorted(np.flatnonzero(tipo_sala[j] < 0), key=lambda r: -e.salas[r]):
            deficit = dem - capjt.sum(0)
            t = int(deficit.argmax()) if deficit.max() > 0 else int(np.argmax(d_esc[j] - capjt[j]))
            tipo_sala[j][r] = t
            capjt[j, t] += e.salas[r]
            _log(traco, f"A3. {e.id} sala {r + 1} ({e.salas[r]}) sobrou -> {NOMES_TIPOS[t]}")
    # A4. cobertura: capacidade de cada tipo >= demanda
    retip = 0
    while True:
        deficit = dem - capjt.sum(0)
        t = int(deficit.argmax())
        if deficit[t] <= 0:
            break
        melhor = None
        for j in range(N):
            for r, u in enumerate(tipo_sala[j]):
                s = inst.escolas[j].salas[r]
                if u != t and -deficit[u] >= s:
                    chave = (-(d_esc[j, t] - capjt[j, t]), s)
                    if melhor is None or chave < melhor[0]:
                        melhor = (chave, j, r)
        if melhor is None:
            raise ErroConstrucao(f"não há como cobrir a demanda do tipo {NOMES_TIPOS[t]} "
                                 f"(falta {deficit[t]} vagas)")
        _, j, r = melhor
        u, s = tipo_sala[j][r], inst.escolas[j].salas[r]
        tipo_sala[j][r] = t
        capjt[j, u] -= s
        capjt[j, t] += s
        retip += 1
        _log(traco, f"A4. {NOMES_TIPOS[t]} sem cobertura (falta {deficit[t]}): {inst.escolas[j].id} sala "
                    f"{r + 1} ({s}) {NOMES_TIPOS[u]} -> {NOMES_TIPOS[t]}")
    _log(traco, "capacidade por tipo: " + " ".join(
        f"{NOMES_TIPOS[t]}={capjt[:, t].sum()}/{dem[t]}" for t in range(T)))
    return tipo_sala, retip


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


def construir(inst, k=1, rng=None, traco=None):
    """Solução inicial viável. Devolve (Solucao, info)."""
    t0 = time.perf_counter()
    tipo_sala, retip = fase_a(inst, traco)
    t1 = time.perf_counter()
    aloc, _ = fase_b(inst, tipo_sala, k, rng, traco)
    t2 = time.perf_counter()
    sol = Solucao(inst, tipo_sala, aloc)
    _log(traco, f"solução inicial: custo {sol.custo:.4f}")
    return sol, {"t_fase_a": t1 - t0, "t_fase_b": t2 - t1, "retipagens": retip}
