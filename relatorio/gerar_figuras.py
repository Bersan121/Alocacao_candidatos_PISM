"""Gera as figuras (PNG, 300 dpi), as tabelas (LaTeX) e as métricas (macros LaTeX) do relatório a
partir dos resultados dos experimentos e das análises. As figuras são sempre imagens, nunca PDF.

O relatório trata só do modelo com até dois tipos de prova por escola (K = 2, `-t 2`).

Entradas:
  resultados/tipos2/resumo.csv, .../execucoes.csv     experimento principal (k = 10, 10 execuções)
  resultados/tipos2/solucoes/<inst>_distribuicao.csv  tipos e candidatos de cada escola na melhor solução
  resultados/tipos2/sensibilidade_k/k*/resumo.csv     sensibilidade ao tamanho da RCL
  analise/resultados/caracteristicas.csv              características das instâncias
  analise/resultados/modelo_exato.csv                 viabilidade, limite inferior e MIP (colunas de K = 2)
Saídas:
  relatorio/figuras/*.png, relatorio/tabelas/*.tex, relatorio/tabelas/metricas.tex

Uso: .venv/bin/python relatorio/gerar_figuras.py
"""
import csv
import statistics as st
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
from instancia import ler_instancia  # noqa: E402

K = 2  # tipos de prova por escola
RES = RAIZ / "resultados" / "tipos2"
ANA = RAIZ / "analise" / "resultados"
FIG = Path(__file__).parent / "figuras"
TAB = Path(__file__).parent / "tabelas"

# paleta categórica validada (ordem fixa) e tokens de texto/grade
SERIE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
TXT1, TXT2, GRADE, FUNDO = "#0b0b0b", "#52514e", "#e6e5e0", "#ffffff"
COR_INI, COR_FIN = SERIE[1], SERIE[0]
TIPOS = ["M1", "M2", "M3e", "M3s", "M3h", "M3d"]
VIZ = ["N1_shift", "N2_swap", "N3_cadeias", "N4_retipar", "N5_trocar", "N6_escola", "N7_trocar_escolas"]
VIZ_ROT = ["N1 shift", "N2 swap", "N3 cadeias", "N4 retipar sala", "N5 trocar salas", "N6 tipo da escola",
           "N7 trocar escolas"]
VIZ_MACRO = ["NUm", "NDois", "NTres", "NQuatro", "NCinco", "NSeis", "NSete"]
KS = [1, 5, 10, 25, 50]
# instâncias citadas no texto do relatório (macro LaTeX -> caminho relativo sem .txt)
CITADAS = {
    "idExemplo": "instancias_pism/instancia1_G8",       # exemplo passo a passo
    "idGrupo": "instancias/instancia_1",                  # instância do grupo (distribuição)
    "idInviavel": "instancias_pism/Instancia1_G2",        # inviável
}

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 8.5, "axes.edgecolor": GRADE, "axes.linewidth": 0.8,
    "axes.labelcolor": TXT2, "xtick.color": TXT2, "ytick.color": TXT2, "text.color": TXT1,
    "axes.grid": True, "axes.axisbelow": True, "grid.color": GRADE, "grid.linewidth": 0.6, "grid.linestyle": "-",
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "figure.facecolor": FUNDO, "axes.facecolor": FUNDO, "savefig.bbox": "tight", "savefig.dpi": 300,
})
LARG = 5.9  # largura útil do modelo SBC (15 cm) em polegadas


def salvar(fig, nome):
    """Grava a figura como imagem PNG (o relatório não usa figuras em PDF)."""
    fig.savefig(FIG / f"{nome}.png")
    plt.close(fig)


def br(x, d=2):
    """Número com vírgula decimal (sem "-0,00")."""
    v = round(x, d) + 0.0
    return f"{v:.{d}f}".replace(".", ",").replace("-0,00", "0,00")


def br_milhar(x, d=2):
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


FMT = FuncFormatter(lambda v, _: br(v, 0) if abs(v - round(v)) < 1e-9 else br(v, 1))


def ler(caminho):
    return list(csv.DictReader(open(caminho)))


def f(x):
    return float(x) if x not in ("", None, "None") else None


def tex_esc(s):
    return s.replace("_", r"\_").replace("&", r"\&").replace("%", r"\%")


# ----------------------------------------------------------------------------- dados
def tipos_escolas(nome):
    """{escola: [tipos com capacidade]} na melhor solução."""
    tipos = {}
    for l in ler(RES / "solucoes" / f"{nome}_distribuicao.csv"):
        if int(l["capacidade"]) > 0:
            tipos.setdefault(l["escola"], []).append(l["tipo"])
    return tipos


def carregar():
    """Lista de todas as instâncias (ordenadas por M); x["d"] traz os resultados (None se inviável)."""
    exato = {r["instancia"]: r for r in ler(ANA / "modelo_exato.csv")}
    resumo = {r["instancia"]: r for r in ler(RES / "resumo.csv")}
    execs = ler(RES / "execucoes.csv")
    todas = []
    for nome, s in exato.items():
        I = ler_instancia(RAIZ / f"{nome}.txt")
        x = {"nome": nome, "M": I.M, "N": I.N, "salas": I.num_salas,
             "folga": 100 * (I.cap.sum() - I.M) / I.M, "d": None}
        if s[f"viavel{K}"] == "1":
            r = resumo[nome]
            d = {"r": r, "execs": [e for e in execs if e["instancia"] == nome]}
            # melhor valor conhecido: MIP, alocação ótima com os tipos da fase A ou a própria heurística
            d["ref"] = min(v for v in (f(s[f"MIP{K}"]), f(s[f"aloc_otima{K}"]), f(r["final_melhor"])) if v)
            d["ref_otima"] = s[f"MIP_otimo{K}"] == "1"
            d["mip"] = f(s[f"MIP{K}"])
            d["lb"] = max(f(s["LB"]), f(s[f"MIP_lb{K}"]) or 0)
            d["ini_media"], d["fin_melhor"] = f(r["inicial_media"]), f(r["final_melhor"])
            d["gap_ini"] = 100 * (d["ini_media"] - d["ref"]) / d["ref"]
            d["gap_fin"] = 100 * (d["fin_melhor"] - d["ref"]) / d["ref"]
            d["gap_lb"] = 100 * (d["fin_melhor"] - d["lb"]) / d["lb"]
            d["tipos"] = tipos_escolas(nome)
            d["duas"] = sum(1 for t in d["tipos"].values() if len(t) == 2)
            x["d"] = d
        todas.append(x)
    todas.sort(key=lambda x: (x["M"], x["nome"]))
    for k, x in enumerate(todas, 1):
        x["id"] = f"I{k:02d}"
    return todas


def viaveis(todas):
    return [x for x in todas if x["d"]]


# ----------------------------------------------------------------------------- figuras
def fig_gaps(todas):
    """Gap até o melhor valor conhecido: solução inicial (média) e após o VND."""
    xs = sorted(viaveis(todas), key=lambda x: x["d"]["gap_fin"])
    fig, ax = plt.subplots(figsize=(LARG, 0.17 * len(xs) + 1.0))
    y = list(range(len(xs)))
    for i, x in zip(y, xs):
        ax.plot([x["d"]["gap_fin"], x["d"]["gap_ini"]], [i, i], color=GRADE, lw=1.5, zorder=1)
    ax.scatter([x["d"]["gap_ini"] for x in xs], y, s=26, color=COR_INI, zorder=3, label="construtivo (média)",
               edgecolor=FUNDO, linewidth=1)
    ax.scatter([x["d"]["gap_fin"] for x in xs], y, s=26, color=COR_FIN, zorder=3, label="após o VND (melhor)",
               edgecolor=FUNDO, linewidth=1)
    ax.set_yticks(y, [x["id"] for x in xs], fontsize=7)
    ax.set_ylim(-0.8, len(xs) - 0.2)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(FMT)
    ax.set_xlabel("gap até o melhor conhecido (%)")
    ax.set_xlim(left=-1)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=7.5, handletextpad=0.2)
    salvar(fig, "gaps")


def participacao(xs, v):
    """Participação média (por instância) da vizinhança v na melhoria total."""
    vals = []
    for x in xs:
        ex = x["d"]["execs"]
        tot = st.mean(f(e["melhoria"]) for e in ex)
        vals.append(100 * st.mean(f(e.get(f"ganho_{v}") or 0) for e in ex) / tot if tot > 0 else 0)
    return st.mean(vals)


def fig_vizinhancas(todas):
    """Participação de cada vizinhança na melhoria total (média por instância)."""
    fig, ax = plt.subplots(figsize=(LARG, 2.2))
    part = [participacao(viaveis(todas), v) for v in VIZ]
    ax.bar(range(len(part)), part, width=0.6, color=COR_FIN, edgecolor=FUNDO, linewidth=1)
    for p, v in enumerate(part):
        ax.text(p, v + 1.5, br(v, 1), ha="center", fontsize=7, color=TXT2)
    ax.set_xticks(range(len(VIZ)), [r.replace(" ", "\n") for r in VIZ_ROT], fontsize=7)
    ax.set_ylabel("% da melhoria total")
    ax.yaxis.set_major_formatter(FMT)
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, max(part) + 10)
    salvar(fig, "vizinhancas")


def fig_tempo(todas):
    """Tempo médio por execução (construtivo + VND) em função do número de candidatos."""
    xs = viaveis(todas)
    fig, ax = plt.subplots(figsize=(LARG, 2.4))
    ax.scatter([x["M"] for x in xs], [f(x["d"]["r"]["t_total_medio"]) for x in xs], s=26, color=COR_FIN,
               edgecolor=FUNDO, linewidth=1, zorder=3)
    ax.set_xlabel("número de candidatos (M)")
    ax.set_ylabel("tempo por execução (s)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: br_milhar(v, 0)))
    ax.yaxis.set_major_formatter(FMT)
    salvar(fig, "tempo")


def fig_variabilidade(todas):
    """Desvio de cada execução em relação à média da instância (valor inicial e final)."""
    xs = viaveis(todas)
    fig, ax = plt.subplots(figsize=(LARG, 2.3))
    for k, x in enumerate(xs):
        ini = [f(e["valor_inicial"]) for e in x["d"]["execs"]]
        fin = [f(e["valor_final"]) for e in x["d"]["execs"]]
        m, mf = st.mean(ini), st.mean(fin)
        ax.scatter([k - 0.15] * len(ini), [100 * (v - m) / m for v in ini], s=9, color=COR_INI,
                   label="construtivo" if k == 0 else None, linewidth=0, alpha=0.85)
        ax.scatter([k + 0.15] * len(fin), [100 * (v - mf) / mf for v in fin], s=9, color=COR_FIN,
                   label="após o VND" if k == 0 else None, linewidth=0)
    ax.axhline(0, color=TXT2, lw=0.6)
    ax.set_xticks(range(len(xs)), [x["id"] for x in xs], rotation=90, fontsize=6.5)
    ax.set_xlim(-0.8, len(xs) - 0.2)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("desvio da média (%)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: br(v, 2)))
    ax.legend(fontsize=7, loc="upper right", ncol=2)
    salvar(fig, "variabilidade")


def fig_distribuicao(nome):
    """Candidatos por escola e tipo de prova na melhor solução de uma instância."""
    linhas = ler(RES / "solucoes" / f"{nome}_distribuicao.csv")
    escolas = sorted(dict.fromkeys(l["escola"] for l in linhas), key=lambda e: int(e.lstrip("E")))
    fig, ax = plt.subplots(figsize=(LARG, 2.4))
    base = [0] * len(escolas)
    for t, tipo in enumerate(TIPOS):
        vals = [sum(int(l["candidatos"]) for l in linhas if l["escola"] == e and l["tipo"] == tipo)
                for e in escolas]
        ax.bar(range(len(escolas)), vals, bottom=base, width=0.72, color=SERIE[t], label=tipo,
               edgecolor=FUNDO, linewidth=1)
        base = [b + v for b, v in zip(base, vals)]
    caps = [sum(int(l["capacidade"]) for l in linhas if l["escola"] == e) for e in escolas]
    ax.scatter(range(len(escolas)), caps, marker="_", s=120, color=TXT1, linewidth=1.2, label="capacidade",
               zorder=4)
    ax.set_xticks(range(len(escolas)), escolas, fontsize=7)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("candidatos")
    ax.set_ylim(0, max(caps) * 1.08)
    ax.legend(ncol=7, fontsize=7, loc="lower center", bbox_to_anchor=(0.5, 1.0), handlelength=1.2,
              columnspacing=1.0)
    salvar(fig, "distribuicao")


# ----------------------------------------------------------------------------- tabelas
def escrever(nome, linhas):
    (TAB / nome).write_text("\n".join(linhas) + "\n")


def tab_instancias(todas):
    l = [r"\begin{tabular}{llrrrrc}", r"\hline",
         r"ID & Arquivo & $M$ & $N$ & Salas & Folga (\%) & Viável \\", r"\hline"]
    for x in todas:
        pasta, arq = x["nome"].split("/", 1)
        marca = "$^\\ddagger$" if pasta == "instancias" else ""
        l.append(f"{x['id']} & \\texttt{{{tex_esc(arq)}}}{marca} & {x['M']} & {x['N']} & {x['salas']} & "
                 f"{br(x['folga'], 1)} & {'sim' if x['d'] else 'não'} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("instancias.tex", l)


def tab_resultados(todas):
    l = [r"\begin{tabular}{lrrrrrrrr}", r"\hline",
         r" & \multicolumn{4}{c}{Construtivo (10 execuções)} & \multicolumn{4}{c}{Após o VND (10 execuções)} \\",
         r"ID & média & desvio & melhor & pior & média & desvio & melhor & pior \\", r"\hline"]
    for x in viaveis(todas):
        r = x["d"]["r"]
        l.append(f"{x['id']} & " + " & ".join(
            br(f(r[c])) for c in ("inicial_media", "inicial_dp", "inicial_melhor", "inicial_pior",
                                  "final_media", "final_dp", "final_melhor", "final_pior")) + r" \\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("resultados.tex", l)


def tab_qualidade(todas):
    """Por instância: melhoria, gaps (inicial, final, LB), tempo médio e escolas da melhor solução."""
    l = [r"\begin{tabular}{l rrrrr cc}", r"\hline",
         r"ID & Melhoria & Gap ini. & Gap final & Gap LB & $t$ & Escolas com & Escolas \\",
         r" & (\%) & (\%) & (\%) & (\%) & (s) & 2 tipos & usadas \\", r"\hline"]
    for x in viaveis(todas):
        d = x["d"]
        marca = "$^*$" if d["ref_otima"] else ""
        l.append(f"{x['id']} & {br(f(d['r']['melhoria_media_pct']))} & {br(d['gap_ini'])} & "
                 f"{br(d['gap_fin'])}{marca} & {br(d['gap_lb'])} & {br(f(d['r']['t_total_medio']))} & "
                 f"{d['duas']}/{x['N']} & {d['r']['escolas_usadas_melhor']}/{x['N']} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("qualidade.tex", l)


def tab_vizinhancas(todas):
    """Movimentos, ganho e participação de cada vizinhança."""
    xs = viaveis(todas)
    l = [r"\begin{tabular}{lrrr}", r"\hline",
         r"Vizinhança & Movimentos & Ganho & \% da melhoria \\", r"\hline"]
    for v, rot in zip(VIZ, VIZ_ROT):
        movs = st.mean(st.mean(f(e.get(f"movs_{v}") or 0) for e in x["d"]["execs"]) for x in xs)
        ganho = st.mean(100 * st.mean(f(e.get(f"ganho_{v}") or 0) for e in x["d"]["execs"]) / x["d"]["ini_media"]
                        for x in xs)
        l.append(f"{rot} & {br(movs, 1)} & {br(ganho, 2)}\\% & {br(participacao(xs, v), 1)} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("vizinhancas.tex", l)


def sensibilidade(todas):
    """Gap médio (inicial e final) e coeficiente de variação para cada k."""
    ref = {x["nome"]: x["d"] for x in viaveis(todas)}
    lin = []
    for k in KS:
        arq = RES / "resumo.csv" if k == 10 else RES / "sensibilidade_k" / f"k{k}" / "resumo.csv"
        if not arq.exists():
            continue
        rs = [r for r in ler(arq) if r["instancia"] in ref]
        g = lambda r, c: 100 * (f(r[c]) - ref[r["instancia"]]["ref"]) / ref[r["instancia"]]["ref"]
        lin.append({
            "k": k, "n": len(rs),
            "gap_ini": st.mean(g(r, "inicial_media") for r in rs),
            "gap_fin_media": st.mean(g(r, "final_media") for r in rs),
            "gap_fin_melhor": st.mean(g(r, "final_melhor") for r in rs),
            "cv_ini": st.mean(100 * f(r["inicial_dp"]) / f(r["inicial_media"]) for r in rs),
            "cv_fin": st.mean(100 * f(r["final_dp"]) / f(r["final_media"]) for r in rs),
            "t": st.mean(f(r["t_total_medio"]) for r in rs),
        })
    return lin


def tab_sensibilidade(lin):
    l = [r"\begin{tabular}{rrrrrrr}", r"\hline",
         r"$k$ & Gap ini. (\%) & Gap final (\%) & Gap final melhor (\%) & CV ini. (\%) & CV final (\%) & $t$ (s) \\",
         r"\hline"]
    for x in lin:
        l.append(f"{x['k']} & {br(x['gap_ini'])} & {br(x['gap_fin_media'], 3)} & {br(x['gap_fin_melhor'], 3)} & "
                 f"{br(x['cv_ini'], 3)} & {br(x['cv_fin'], 3)} & {br(x['t'], 2)} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("sensibilidade_k.tex", l)


def tab_distribuicao(nome):
    """Resumo por escola da melhor solução: tipos, candidatos, ocupação e distância média."""
    I = ler_instancia(RAIZ / f"{nome}.txt")
    res = {}
    for l in ler(RES / "solucoes" / f"{nome}_distribuicao.csv"):
        t, n, d = res.get(l["escola"], ([], 0, 0.0))
        cap, cand = int(l["capacidade"]), int(l["candidatos"])
        res[l["escola"]] = (t + ([f"{l['tipo']} ({cap})"] if cap > 0 else []), n + cand,
                            d + cand * f(l["dist_media"]))
    l = [r"\begin{tabular}{lrlrrr}", r"\hline",
         r"Escola & Cap. & Tipos (vagas) & Cand. & Ocup. (\%) & Dist. média \\", r"\hline"]
    for j, e in enumerate(I.escolas):
        cap = int(I.cap[j])
        t, n, d = res.get(e.id, ([], 0, 0.0))
        l.append(f"{e.id} & {cap} & {' + '.join(t) or '--'} & {n} & {br(100 * n / cap, 1)} & "
                 f"{br(d / n if n else 0, 3)} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("distribuicao.tex", l)


# ----------------------------------------------------------------------------- métricas
def metricas(todas, lin):
    m = {}
    por_nome = {x["nome"]: x for x in todas}
    xs = viaveis(todas)
    m["nTotal"] = str(len(todas))
    m["Mmin"], m["Mmax"] = str(min(x["M"] for x in todas)), str(max(x["M"] for x in todas))
    m["Nmin"], m["Nmax"] = str(min(x["N"] for x in todas)), str(max(x["N"] for x in todas))
    m["folgaMin"] = br(min(x["folga"] for x in todas), 1)
    m["folgaMax"] = br(max(x["folga"] for x in todas), 1)
    car = ler(ANA / "caracteristicas.csv")
    m["fracSobreMin"] = br(100 * min(f(r["frac_sobrecarga"]) for r in car), 0)
    m["fracSobreMax"] = br(100 * max(f(r["frac_sobrecarga"]) for r in car), 0)
    m["sobrecargaMax"] = br(max(f(r["sobrecarga_max"]) for r in car), 1)
    for k, nome in CITADAS.items():
        m[k] = por_nome[nome]["id"]
    g = lambda c: [x["d"][c] for x in xs]
    m["nInst"] = str(len(xs))
    m["nExec"] = str(sum(len(x["d"]["execs"]) for x in xs))
    m["gapIni"] = br(st.mean(g("gap_ini")))
    m["gapFin"] = br(st.mean(g("gap_fin")))
    m["gapLb"] = br(st.mean(g("gap_lb")))
    m["gapLbMediana"] = br(st.median(g("gap_lb")))
    m["melhoria"] = br(st.mean(f(x["d"]["r"]["melhoria_media_pct"]) for x in xs))
    m["refOtima"] = str(sum(1 for x in xs if x["d"]["ref_otima"]))
    m["otimos"] = str(sum(1 for x in xs if x["d"]["ref_otima"] and x["d"]["gap_fin"] < 1e-3))
    m["abaixoUm"] = str(sum(1 for x in xs if x["d"]["gap_fin"] < 1))
    m["acimaCinco"] = str(sum(1 for x in xs if x["d"]["gap_fin"] >= 5))
    m["refHeur"] = str(sum(1 for x in xs if abs(x["d"]["fin_melhor"] - x["d"]["ref"]) < 1e-6
                           and not x["d"]["ref_otima"]))
    m["melhorQueMip"] = str(sum(1 for x in xs if x["d"]["mip"] and x["d"]["fin_melhor"] < x["d"]["mip"] - 1e-6))
    m["semMip"] = str(sum(1 for x in xs if not x["d"]["mip"]))
    lbs = sorted(xs, key=lambda x: -x["d"]["gap_lb"])[:2]
    m["lbFracoIds"] = " e ".join(x["id"] for x in lbs)
    m["lbFracoGaps"] = " e ".join(br(x["d"]["gap_lb"], 1) for x in lbs)
    m["gapLbSemFracos"] = br(st.mean(x["d"]["gap_lb"] for x in xs if x not in lbs))
    m["tempoMedio"] = br(st.mean(f(x["d"]["r"]["t_total_medio"]) for x in xs), 2)
    lenta = max(xs, key=lambda x: f(x["d"]["r"]["t_total_medio"]))
    m["tempoMax"], m["tempoMaxId"] = br(f(lenta["d"]["r"]["t_total_medio"]), 2), lenta["id"]
    m["tConstrMax"] = br(max(f(x["d"]["r"]["t_construtivo_medio"]) for x in xs), 3)
    m["cvIni"] = br(st.mean(100 * f(x["d"]["r"]["inicial_dp"]) / f(x["d"]["r"]["inicial_media"]) for x in xs), 3)
    m["cvIniMax"] = br(max(100 * f(x["d"]["r"]["inicial_dp"]) / f(x["d"]["r"]["inicial_media"]) for x in xs), 3)
    m["cvFinMax"] = br(max(100 * f(x["d"]["r"]["final_dp"]) / f(x["d"]["r"]["final_media"]) for x in xs), 3)
    varia = [x for x in xs if f(x["d"]["r"]["final_dp"]) > 1e-6]
    m["nVariaFin"] = str(len(varia))
    m["variaFinIds"] = ", ".join(x["id"] for x in varia) or "nenhuma"
    for n, x in enumerate(sorted(xs, key=lambda x: -x["d"]["gap_fin"])[:3]):
        p = ["Um", "Dois", "Tres"][n]
        m[f"pior{p}Id"], m[f"pior{p}Gap"] = x["id"], br(x["d"]["gap_fin"], 1)
        m[f"pior{p}N"], m[f"pior{p}M"] = str(x["N"]), str(x["M"])
        m[f"pior{p}Salas"] = str(x["salas"])
    rep = [x for x in xs if any(e["reparo_faseA"] == "1" for e in x["d"]["execs"])]
    m["reparoInst"] = str(len(rep))
    m["reparoIds"] = ", ".join(x["id"] for x in rep) if rep else "nenhuma"
    ret = [max(int(e["retipagens_faseA"]) for e in x["d"]["execs"]) for x in xs]
    m["coberturaInst"] = str(sum(1 for r in ret if r > 0))
    for v, mv in zip(VIZ, VIZ_MACRO):
        m[f"part{mv}"] = br(participacao(xs, v), 1)
    ex = [(e, x) for x in xs for e in x["d"]["execs"]]
    tb = [f(e["t_busca"]) for e, _ in ex]
    m["corrTempoM"] = br(st.correlation(tb, [x["M"] for _, x in ex]))
    m["corrTempoTipos"] = br(st.correlation(tb, [sum(f(e[f"movs_{v}"]) for v in VIZ[3:]) for e, _ in ex]))
    fech = [x for x in xs if int(x["d"]["r"]["escolas_usadas_melhor"]) < x["N"]]
    m["nFechou"] = str(len(fech))
    m["fechouIds"] = ", ".join(x["id"] for x in fech) or "nenhuma"
    duas = [100 * x["d"]["duas"] / x["N"] for x in xs]
    m["duasMedia"] = br(st.mean(duas), 1)
    m["duasMin"], m["duasMax"] = br(min(duas), 0), br(max(duas), 0)
    m["nTodasDuas"] = str(sum(1 for v in duas if v > 100 - 1e-9))
    # instâncias citadas: valores e gaps
    for k, nome in CITADAS.items():
        x, suf = por_nome[nome], k[2:]
        if x["d"]:
            m[f"final{suf}"] = br(x["d"]["fin_melhor"])
            m[f"ref{suf}"] = br(x["d"]["ref"])
            m[f"gap{suf}"] = br(x["d"]["gap_fin"], 1)
            m[f"duas{suf}"] = str(x["d"]["duas"])
    linhas = ["% gerado por relatorio/gerar_figuras.py -- não editar"]
    linhas += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in m.items()]
    escrever("metricas.tex", linhas)
    return m


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    for antiga in FIG.glob("*.pdf"):        # versões antigas das figuras em PDF
        antiga.unlink()
    for antiga in ("modelos.png", "tipos_por_sala.png", "tipos_por_escola.png"):
        (FIG / antiga).unlink(missing_ok=True)
    for antiga in ("tipos_por_sala.tex", "tipos_por_escola.tex", "resultados_tipos2.tex"):
        (TAB / antiga).unlink(missing_ok=True)
    todas = carregar()
    lin = sensibilidade(todas)
    fig_gaps(todas)
    fig_vizinhancas(todas)
    fig_tempo(todas)
    fig_variabilidade(todas)
    fig_distribuicao(CITADAS["idGrupo"])
    tab_instancias(todas)
    tab_resultados(todas)
    tab_qualidade(todas)
    tab_vizinhancas(todas)
    tab_sensibilidade(lin)
    tab_distribuicao(CITADAS["idGrupo"])
    m = metricas(todas, lin)
    for k, v in m.items():
        print(f"{k:22s} {v}")
    print(f"k testados: {[l['k'] for l in lin]}")


if __name__ == "__main__":
    main()
