"""Experimentos: construtivo + VND em várias instâncias e execuções.

Uso:
    python src/experimentos.py [opções] [instancia_ou_pasta ...]

    Sem instâncias: usa instancias/ e instancias_pism/ (arquivos .txt, sem conteúdo repetido).
    -r, --execucoes R   execuções por instância, com sementes 0..R-1 (padrão 10; 1 se k = 1)
    -k K                tamanho da RCL da fase B (padrão 10; k = 1 é determinístico)
    --limite S          limite de tempo do VND em segundos (padrão: sem limite)
    --sem-busca         só o construtivo
    --traco             grava o passo a passo (fase A, fase B e cada movimento do VND) da
                        1ª execução de cada instância; use em instâncias pequenas
    -o, --saida DIR     pasta dos resultados (padrão resultados/)

Artefatos (em DIR):
    execucoes.csv                   uma linha por (instância, execução): valor inicial, valor após
                                    a busca local, melhoria, tempos, escolas/salas usadas e
                                    movimentos/ganho de cada vizinhança
    resumo.csv                      por instância: média, desvio, melhor e pior do valor inicial e
                                    final, melhoria média e tempo médio
    solucoes/<pasta>/<inst>.txt     melhor solução: tipo e ocupação de cada sala e alocação de
                                    cada candidato
    solucoes/<pasta>/<inst>_distribuicao.csv
                                    candidatos por escola e tipo (salas, capacidade, ocupação,
                                    distância média) na melhor solução
    traco/<pasta>/<inst>.txt        passo a passo (com --traco)
"""
import argparse
import csv
import statistics as st
import sys
import time
from pathlib import Path

import numpy as np

from busca_local import NOMES, BuscaLocal
from construtivo import ErroConstrucao, construir
from instancia import PASTAS_PADRAO, RAIZ, ErroInstancia, ler_instancia, listar_instancias, rotulo


def executar(inst, nome, semente, k, busca, limite, traco):
    rng = np.random.default_rng(semente)
    t0 = time.perf_counter()
    sol, info = construir(inst, k, rng, traco)
    t1 = time.perf_counter()
    erros = sol.verificar()
    if erros:
        raise AssertionError("solução inicial inviável: " + "; ".join(erros[:5]))
    inicial = sol.custo
    bl = BuscaLocal(sol, traco)
    if busca:
        bl.vnd(limite)
    t2 = time.perf_counter()
    erros = sol.verificar()
    if erros:
        raise AssertionError("solução final inviável: " + "; ".join(erros[:5]))
    r = {
        "instancia": nome, "M": inst.M, "N": inst.N,
        "salas": inst.num_salas, "execucao": semente, "k": k, "valor_inicial": inicial, "valor_final": sol.custo,
        "melhoria": inicial - sol.custo, "melhoria_pct": 100 * (inicial - sol.custo) / inicial if inicial else 0,
        "t_construtivo": t1 - t0, "t_busca": t2 - t1, "t_total": t2 - t0,
        "retipagens_faseA": info["retipagens"],
        "escolas_usadas": sol.escolas_usadas(), "salas_usadas": sol.salas_usadas(),
        "dist_media": sol.custo / inst.M,
    }
    for n in NOMES:
        r[f"movs_{n}"] = bl.stats[n]["movs"]
        r[f"ganho_{n}"] = bl.stats[n]["ganho"]
    return r, sol


def resumir(linhas):
    ini = [r["valor_inicial"] for r in linhas]
    fin = [r["valor_final"] for r in linhas]
    dp = lambda v: st.stdev(v) if len(v) > 1 else 0.0
    melhor = min(linhas, key=lambda r: r["valor_final"])
    return {
        "instancia": linhas[0]["instancia"], "M": linhas[0]["M"], "N": linhas[0]["N"],
        "salas": linhas[0]["salas"], "execucoes": len(linhas),
        "k": linhas[0]["k"],
        "inicial_media": st.mean(ini), "inicial_dp": dp(ini), "inicial_melhor": min(ini), "inicial_pior": max(ini),
        "final_media": st.mean(fin), "final_dp": dp(fin), "final_melhor": min(fin), "final_pior": max(fin),
        "melhoria_media_pct": st.mean(r["melhoria_pct"] for r in linhas),
        "t_construtivo_medio": st.mean(r["t_construtivo"] for r in linhas),
        "t_busca_medio": st.mean(r["t_busca"] for r in linhas),
        "t_total_medio": st.mean(r["t_total"] for r in linhas),
        "escolas_usadas_melhor": melhor["escolas_usadas"], "salas_usadas_melhor": melhor["salas_usadas"],
        "execucao_melhor": melhor["execucao"],
    }


def gravar_csv(caminho, linhas):
    if not linhas:
        return
    with open(caminho, "w", newline="") as f:
        w = csv.DictWriter(f, list(linhas[0].keys()))
        w.writeheader()
        for r in linhas:
            w.writerow({c: (f"{v:.12g}" if isinstance(v, float) else v) for c, v in r.items()})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("instancias", nargs="*")
    ap.add_argument("-r", "--execucoes", type=int, default=10)
    ap.add_argument("-k", type=int, default=10)
    ap.add_argument("--limite", type=float, default=None)
    ap.add_argument("--sem-busca", action="store_true")
    ap.add_argument("--traco", action="store_true")
    ap.add_argument("-o", "--saida", default=str(RAIZ / "resultados"))
    a = ap.parse_args()
    if a.k < 1:
        ap.error("k deve ser >= 1")
    reps = 1 if a.k == 1 else a.execucoes
    saida = Path(a.saida)
    (saida / "solucoes").mkdir(parents=True, exist_ok=True)
    if a.traco:
        (saida / "traco").mkdir(exist_ok=True)

    todas, resumo = [], []
    for arq in listar_instancias(a.instancias or PASTAS_PADRAO):
        try:
            inst = ler_instancia(arq)
        except ErroInstancia as e:
            print(f"ERRO de leitura: {e}", file=sys.stderr)
            continue
        nome = rotulo(arq)
        linhas, melhor = [], None
        try:
            for sem in range(reps):
                tr = None
                if a.traco and sem == 0:
                    (saida / "traco" / nome).parent.mkdir(parents=True, exist_ok=True)
                    tr = open(saida / "traco" / f"{nome}.txt", "w")
                try:
                    r, sol = executar(inst, nome, sem, a.k, not a.sem_busca, a.limite, tr)
                finally:
                    if tr:
                        tr.close()
                linhas.append(r)
                if melhor is None or sol.custo < melhor[1].custo:
                    melhor = (sem, sol)
        except ErroConstrucao as e:
            print(f"{nome:42s} INVIÁVEL: {e}", flush=True)
            continue
        res = resumir(linhas)
        todas += linhas
        resumo.append(res)
        sem, sol = melhor
        base = saida / "solucoes" / nome
        base.parent.mkdir(parents=True, exist_ok=True)
        sol.escrever(f"{base}.txt",
                     [f"instancia: {nome}", f"k: {a.k}  execucao (semente): {sem}"])
        with open(f"{base}_distribuicao.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["escola", "tipo", "salas", "capacidade", "candidatos", "ocupacao_pct", "dist_media"])
            w.writerows([(*l[:5], f"{l[5]:.1f}", f"{l[6]:.4f}") for l in sol.distribuicao()])
        print(f"{nome:42s} M={inst.M:5d} N={inst.N:2d}  inicial {res['inicial_media']:12.2f} "
              f"± {res['inicial_dp']:8.2f}  final {res['final_media']:12.2f} ± {res['final_dp']:8.2f} "
              f"(melhor {res['final_melhor']:.2f})  melhoria {res['melhoria_media_pct']:5.2f}%  "
              f"escolas {res['escolas_usadas_melhor']}/{inst.N}  t={res['t_total_medio']:.2f}s", flush=True)
        gravar_csv(saida / "execucoes.csv", todas)
        gravar_csv(saida / "resumo.csv", resumo)


if __name__ == "__main__":
    main()
