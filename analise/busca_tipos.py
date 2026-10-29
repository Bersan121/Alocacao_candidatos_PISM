"""Referência para K = 1 (um tipo por escola) nas instâncias em que o MIP não fecha: busca local nos
tipos das escolas com avaliação EXATA de cada vizinho (alocação ótima por transporte), partindo dos
tipos da melhor solução da heurística (resultados/solucoes).

Vizinhos: mudar o tipo de uma escola; trocar os tipos de duas escolas. First improvement, só
vizinhos que cobrem a demanda de todos os tipos, limite de tempo por instância. Mede quanto a
avaliação gulosa das vizinhanças de tipo (N6/N7 do VND) deixa de ganhar.

Grava analise/resultados/busca_tipos.csv (instancia, inicial, final, t).
Uso: .venv/bin/python analise/busca_tipos.py [limite_s]   (padrão 120 s por instância)
"""
import csv
import sys
import time

import numpy as np

from comum import RAIZ, SAIDA, T, TIPOS, instancias, transporte


def capacidade(inst, tipo):
    capjt = np.zeros((inst.N, T), int)
    capjt[np.arange(inst.N), tipo] = inst.cap
    return capjt


def tipos_da_solucao(inst, nome):
    """Tipo de cada escola na melhor solução de resultados/solucoes (K = 1)."""
    linhas = open(RAIZ / "resultados" / "solucoes" / f"{nome}.txt").read().splitlines()
    ini = linhas.index("# SALAS (escola, sala, capacidade, tipo, ocupacao)") + 1
    pos = {e.id: j for j, e in enumerate(inst.escolas)}
    tipo = np.zeros(inst.N, int)
    for l in linhas[ini:]:
        if l.startswith("#"):
            break
        e, _, _, t, _ = [c.strip() for c in l.split(",")]
        tipo[pos[e]] = TIPOS.index(t)
    return tipo


def busca(inst, tipo, limite):
    dem, N, t0 = inst.demanda(), inst.N, time.time()
    valor = transporte(inst, capacidade(inst, tipo))
    melhorou = True
    while melhorou and time.time() - t0 < limite:
        melhorou = False
        viz = [(j, t) for j in range(N) for t in range(T) if t != tipo[j]]
        viz += [(j, -(k + 1)) for j in range(N) for k in range(j + 1, N) if tipo[j] != tipo[k]]
        for j, m in viz:
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
            if time.time() - t0 > limite:
                break
    return valor


def main():
    limite = float(sys.argv[1]) if len(sys.argv) > 1 else 120
    viaveis = {r["instancia"] for r in csv.DictReader(open(SAIDA / "modelo_exato.csv")) if r["viavel1"] == "1"}
    linhas = []
    for nome, inst in instancias():
        if nome not in viaveis:
            continue
        tipo = tipos_da_solucao(inst, nome)
        t0 = time.time()
        ini = transporte(inst, capacidade(inst, tipo))
        fim = busca(inst, tipo, limite)
        linhas.append({"instancia": nome, "inicial": ini, "final": fim, "t": round(time.time() - t0, 1)})
        print(f"{nome:36s} {ini:12.2f} -> {fim:12.2f} ({100 * (ini - fim) / ini:5.2f}%)  {linhas[-1]['t']}s", flush=True)
    with open(SAIDA / "busca_tipos.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["instancia", "inicial", "final", "t"])
        w.writeheader()
        w.writerows(linhas)


if __name__ == "__main__":
    main()
