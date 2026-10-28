"""Caracterização das instâncias (o que orientou o projeto da heurística).

Para cada instância: tamanho, folga de capacidade, demanda por tipo, capacidade das escolas e das
salas, grupos de candidatos idênticos e a pressão de capacidade (carga que cada escola receberia se
cada candidato fosse para a escola mais próxima). LB0 = soma das distâncias à escola mais próxima
(ignora tipo e capacidade).

Grava analise/resultados/caracteristicas.csv.
Uso: .venv/bin/python analise/caracteristicas.py
"""
import csv

import numpy as np

from comum import SAIDA, T, TIPOS, grupos, instancias


def caracterizar(nome, inst):
    M, D, cap = inst.M, inst.D, inst.cap
    dem = inst.demanda()
    salas = [s for e in inst.escolas for s in e.salas]
    prox = D.argmin(1)
    carga = np.bincount(prox, minlength=inst.N) / cap      # carga relativa se todos fossem à mais próxima
    return {
        "instancia": nome, "M": M, "N": inst.N, "salas": len(salas),
        "folga_pct": round(100 * (cap.sum() - M) / M, 2),
        "grupos": len(grupos(inst)[0]),
        "cap_escola_min": cap.min(), "cap_escola_max": cap.max(),
        "sala_min": min(salas), "sala_max": max(salas),
        **{f"dem_{TIPOS[t]}": dem[t] for t in range(T)},
        "d_medio": round(D.mean(), 4), "d_mais_prox": round(D.min(1).mean(), 4),
        "sobrecarga_max": round(carga.max(), 3),
        "frac_sobrecarga": round((carga[prox] > 1).mean(), 3),   # candidatos cuja mais próxima lota
        "LB0": round(D.min(1).sum(), 4),
    }


def main():
    SAIDA.mkdir(exist_ok=True)
    linhas = []
    for nome, inst in instancias():
        r = caracterizar(nome, inst)
        linhas.append(r)
        print(f"{nome:40s} M={r['M']:<5d} N={r['N']:<3d} salas={r['salas']:<4d} folga={r['folga_pct']:5.1f}%  "
              f"sobrecarga_max={r['sobrecarga_max']:.2f}  frac_sobrecarga={r['frac_sobrecarga']:.2f}", flush=True)
    with open(SAIDA / "caracteristicas.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)


if __name__ == "__main__":
    main()
