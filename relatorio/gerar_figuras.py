"""Gera as figuras (PNG, 300 dpi), as tabelas (LaTeX) e as métricas (macros LaTeX) do relatório a
partir dos resultados dos experimentos e das análises. As figuras são sempre imagens, nunca PDF.

Entradas:
  resultados/resumo.csv, resultados/execucoes.csv     experimento principal (k = 10, 10 execuções,
                                                      um tipo de prova por escola)
  resultados/tipos2/resumo.csv, .../execucoes.csv     mesmo experimento com até dois tipos por escola
  resultados[/tipos2]/solucoes/<inst>_distribuicao.csv   tipos de cada escola na melhor solução
  resultados/sensibilidade_k/k*/resumo.csv            sensibilidade ao tamanho da RCL (um tipo)
  analise/resultados/caracteristicas.csv              características das instâncias
  analise/resultados/modelo_exato.csv                 viabilidade, limite inferior e MIP (K = 1 e 2)
  analise/resultados/busca_tipos.csv                  busca exata nos tipos das escolas (K = 1)
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

RES = {1: RAIZ / "resultados", 2: RAIZ / "resultados" / "tipos2"}
ANA = RAIZ / "analise" / "resultados"
FIG = Path(__file__).parent / "figuras"
TAB = Path(__file__).parent / "tabelas"

# paleta categórica validada (ordem fixa) e tokens de texto/grade
SERIE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
TXT1, TXT2, GRADE, FUNDO = "#0b0b0b", "#52514e", "#e6e5e0", "#ffffff"
COR_K = {1: SERIE[0], 2: SERIE[2]}
ROT_K = {1: "1 tipo por escola", 2: "até 2 tipos por escola"}
TIPOS = ["M1", "M2", "M3e", "M3s", "M3h", "M3d"]
VIZ = ["N1_shift", "N2_swap", "N3_cadeias", "N4_retipar", "N5_trocar", "N6_escola", "N7_trocar_escolas"]
VIZ_ROT = ["N1 shift", "N2 swap", "N3 cadeias", "N4 retipar sala", "N5 trocar salas", "N6 tipo da escola",
           "N7 trocar escolas"]
KS = [1, 5, 10, 25, 50]
# instâncias citadas no texto do relatório (macro LaTeX -> caminho relativo sem .txt)
CITADAS = {
    "idExemplo": "instancias_pism/instancia1_G8",       # exemplo passo a passo
    "idGrupo": "instancias/instancia_1",                  # instância do grupo (distribuição)
    "idInviavel": "instancias_pism/Instancia1_G2",        # inviável com 1 e com 2 tipos
}

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 8.5, "axes.edgecolor": GRADE, "axes.linewidth": 0.8,
    "axes.labelcolor": TXT2, "xtick.color": TXT2, "ytick.color": TXT2, "text.color": TXT1,
    "axes.grid": True, "grid.color": GRADE, "grid.linewidth": 0.6, "grid.linestyle": "-",
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
def tipos_escolas(K, nome):
    """{escola: [tipos com capacidade]} na melhor solução com até K tipos por escola."""
    tipos = {}
    for l in ler(RES[K] / "solucoes" / f"{nome}_distribuicao.csv"):
        if int(l["capacidade"]) > 0:
            tipos.setdefault(l["escola"], []).append(l["tipo"])
    return tipos


def carregar():
    """Lista de todas as instâncias (ordenadas por M), com os resultados de cada K em x[K]."""
    exato = {r["instancia"]: r for r in ler(ANA / "modelo_exato.csv")}
    btipos = {r["instancia"]: f(r["final"]) for r in ler(ANA / "busca_tipos.csv")}
    resumo = {K: {r["instancia"]: r for r in ler(RES[K] / "resumo.csv")} for K in (1, 2)}
    execs = {K: ler(RES[K] / "execucoes.csv") for K in (1, 2)}
    todas = []
    for nome, s in exato.items():
        I = ler_instancia(RAIZ / f"{nome}.txt")
        x = {"nome": nome, "M": I.M, "N": I.N, "salas": I.num_salas,
             "folga": 100 * (I.cap.sum() - I.M) / I.M, "lb_transp": f(s["LB"])}
        for K in (1, 2):
            if s[f"viavel{K}"] != "1":
                x[K] = None
                continue
            r = resumo[K][nome]
            d = {"r": r, "execs": [e for e in execs[K] if e["instancia"] == nome]}
            # melhor valor conhecido: MIP, alocação ótima com os tipos da fase A, busca exata nos
            # tipos (só K = 1) ou a própria heurística
            d["btipos"] = btipos.get(nome) if K == 1 else None
            d["ref"] = min(v for v in (f(s[f"MIP{K}"]), f(s[f"aloc_otima{K}"]), d["btipos"],
                                       f(r["final_melhor"])) if v)
            d["ref_otima"] = s[f"MIP_otimo{K}"] == "1"
            d["mip"] = f(s[f"MIP{K}"])
            d["lb"] = max(f(s["LB"]), f(s[f"MIP_lb{K}"]) or 0)
            d["ini_media"], d["fin_melhor"] = f(r["inicial_media"]), f(r["final_melhor"])
            d["gap_ini"] = 100 * (d["ini_media"] - d["ref"]) / d["ref"]
            d["gap_fin"] = 100 * (d["fin_melhor"] - d["ref"]) / d["ref"]
            d["gap_lb"] = 100 * (d["fin_melhor"] - d["lb"]) / d["lb"]
            d["gap_transp"] = 100 * (d["fin_melhor"] - x["lb_transp"]) / x["lb_transp"]
            d["tipos"] = tipos_escolas(K, nome)
            d["duas"] = sum(1 for t in d["tipos"].values() if len(t) == 2)
            x[K] = d
        if x[1] and x[2]:
            x["reducao"] = 100 * (x[1]["fin_melhor"] - x[2]["fin_melhor"]) / x[1]["fin_melhor"]
            # fração do intervalo [LB de transporte, valor com um tipo] eliminada ao permitir dois
            x["fechado"] = 100 * (x[1]["fin_melhor"] - x[2]["fin_melhor"]) / (x[1]["fin_melhor"] - x["lb_transp"])
        todas.append(x)
    todas.sort(key=lambda x: (x["M"], x["nome"]))
    for k, x in enumerate(todas, 1):
        x["id"] = f"I{k:02d}"
    return todas


def viaveis(todas, K):
    return [x for x in todas if x[K]]


# ----------------------------------------------------------------------------- figuras
def fig_gaps(todas):
    """Gap até o melhor valor conhecido: solução inicial (média) e após o VND, para cada K."""
    xs = [x for x in todas if x[1] or x[2]]
    xs.sort(key=lambda x: (x[1] or x[2])["gap_fin"] if x[1] else 1e9)
    fig, axs = plt.subplots(1, 2, figsize=(LARG, 0.17 * len(xs) + 1.1), sharey=True)
    y = list(range(len(xs)))
    for ax, K in zip(axs, (1, 2)):
        for i, x in zip(y, xs):
            if x[K]:
                ax.plot([x[K]["gap_fin"], x[K]["gap_ini"]], [i, i], color=GRADE, lw=1.5, zorder=1)
        pts = [(i, x[K]) for i, x in zip(y, xs) if x[K]]
        ax.scatter([d["gap_ini"] for _, d in pts], [i for i, _ in pts], s=22, color=SERIE[1], zorder=3,
                   label="construtivo (média)", edgecolor=FUNDO, linewidth=1)
        ax.scatter([d["gap_fin"] for _, d in pts], [i for i, _ in pts], s=22, color=COR_K[K], zorder=3,
                   label=f"após o VND ({ROT_K[K]})", edgecolor=FUNDO, linewidth=1)
        ax.set_title(ROT_K[K], fontsize=8.5, color=TXT1)
        ax.grid(axis="y", visible=False)
        ax.xaxis.set_major_formatter(FMT)
        ax.set_xlabel("gap até o melhor conhecido (%)")
        ax.set_xlim(left=-1)
    h0, l0 = axs[0].get_legend_handles_labels()
    h1, l1 = axs[1].get_legend_handles_labels()
    fig.legend(h0 + h1[1:], l0 + l1[1:], loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3,
               fontsize=7.5, handletextpad=0.2)
    fig.tight_layout()
    axs[0].set_yticks(y, [x["id"] for x in xs], fontsize=7)
    axs[0].set_ylim(-0.8, len(xs) - 0.2)
    salvar(fig, "gaps")


def participacao(xs, v, K):
    """Participação média (por instância) da vizinhança v na melhoria total."""
    vals = []
    for x in xs:
        ex = x[K]["execs"]
        tot = st.mean(f(e["melhoria"]) for e in ex)
        vals.append(100 * st.mean(f(e.get(f"ganho_{v}") or 0) for e in ex) / tot if tot > 0 else 0)
    return st.mean(vals)


def fig_vizinhancas(todas):
    """Participação de cada vizinhança na melhoria total (média por instância), para cada K."""
    fig, ax = plt.subplots(figsize=(LARG, 2.4))
    larg = 0.38
    for K, desl in ((1, -larg / 2), (2, larg / 2)):
        part = [participacao(viaveis(todas, K), v, K) for v in VIZ]
        pos = [p + desl for p in range(len(part))]
        ax.bar(pos, part, width=larg, color=COR_K[K], edgecolor=FUNDO, linewidth=1, label=ROT_K[K])
        for p, v in zip(pos, part):
            ax.text(p, v + 1.5, br(v, 1), ha="center", fontsize=6, color=TXT2)
    ax.set_xticks(range(len(VIZ)), [r.replace(" ", "\n") for r in VIZ_ROT], fontsize=7)
    ax.set_ylabel("% da melhoria total")
    ax.yaxis.set_major_formatter(FMT)
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, 105)
    ax.legend(fontsize=7.5, loc="upper right")
    salvar(fig, "vizinhancas")


def fig_tempo(todas):
    """Tempo médio por execução (construtivo + VND) em função do número de candidatos, para cada K."""
    fig, ax = plt.subplots(figsize=(LARG, 2.4))
    for K in (1, 2):
        xs = viaveis(todas, K)
        ax.scatter([x["M"] for x in xs], [f(x[K]["r"]["t_total_medio"]) for x in xs], s=26, color=COR_K[K],
                   edgecolor=FUNDO, linewidth=1, zorder=3, label=ROT_K[K])
    ax.set_xlabel("número de candidatos (M)")
    ax.set_ylabel("tempo por execução (s)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: br_milhar(v, 0)))
    ax.yaxis.set_major_formatter(FMT)
    ax.legend(fontsize=7.5, loc="upper left")
    salvar(fig, "tempo")


def fig_variabilidade(todas):
    """Desvio de cada execução em relação à média da instância (valor inicial e final), para cada K."""
    fig, axs = plt.subplots(2, 1, figsize=(LARG, 4.2))
    for ax, K in zip(axs, (1, 2)):
        xs = viaveis(todas, K)
        for k, x in enumerate(xs):
            ini = [f(e["valor_inicial"]) for e in x[K]["execs"]]
            fin = [f(e["valor_final"]) for e in x[K]["execs"]]
            m, mf = st.mean(ini), st.mean(fin)
            ax.scatter([k - 0.15] * len(ini), [100 * (v - m) / m for v in ini], s=9, color=SERIE[1],
                       label="construtivo" if k == 0 else None, linewidth=0, alpha=0.85)
            ax.scatter([k + 0.15] * len(fin), [100 * (v - mf) / mf for v in fin], s=9, color=COR_K[K],
                       label="após o VND" if k == 0 else None, linewidth=0)
        ax.axhline(0, color=TXT2, lw=0.6)
        ax.set_xticks(range(len(xs)), [x["id"] for x in xs], rotation=90, fontsize=6.5)
        ax.set_xlim(-0.8, len(xs) - 0.2)
        ax.grid(axis="x", visible=False)
        ax.set_ylabel("desvio da média (%)")
        ax.set_title(ROT_K[K], fontsize=8.5, color=TXT1)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: br(v, 2)))
        ax.legend(fontsize=7, loc="upper right", ncol=2)
    fig.tight_layout()
    salvar(fig, "variabilidade")


def fig_tipos_por_escola(todas):
    """Gap até o limite inferior de transporte da melhor solução com um e com até dois tipos."""
    xs = sorted(viaveis(todas, 2), key=lambda x: x[2]["gap_transp"])
    fig, ax = plt.subplots(figsize=(LARG, 0.17 * len(xs) + 1.0))
    y = list(range(len(xs)))
    for i, x in zip(y, xs):
        if x[1]:
            ax.plot([x[2]["gap_transp"], x[1]["gap_transp"]], [i, i], color=GRADE, lw=1.5, zorder=1)
    um = [(i, x[1]["gap_transp"]) for i, x in zip(y, xs) if x[1]]
    ax.scatter([g for _, g in um], [i for i, _ in um], s=26, color=COR_K[1], zorder=3,
               label=ROT_K[1], edgecolor=FUNDO, linewidth=1)
    ax.scatter([x[2]["gap_transp"] for x in xs], y, s=26, color=COR_K[2], zorder=3, label=ROT_K[2],
               edgecolor=FUNDO, linewidth=1)
    ax.set_yticks(y, [x["id"] + ("$^\\dagger$" if not x[1] else "") for x in xs], fontsize=7)
    ax.set_ylim(-0.8, len(xs) - 0.2)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(FMT)
    ax.set_xlabel("gap até o limite inferior de transporte (%)")
    ax.set_xlim(left=-1)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=7.5, handletextpad=0.2)
    salvar(fig, "tipos_por_escola")


def fig_distribuicao(nome):
    """Candidatos por escola e tipo de prova na melhor solução de uma instância, para cada K."""
    fig, axs = plt.subplots(2, 1, figsize=(LARG, 4.4), sharex=True)
    for ax, K in zip(axs, (1, 2)):
        linhas = ler(RES[K] / "solucoes" / f"{nome}_distribuicao.csv")
        escolas = sorted(dict.fromkeys(l["escola"] for l in linhas), key=lambda e: int(e.lstrip("E")))
        base = [0] * len(escolas)
        for t, tipo in enumerate(TIPOS):
            vals = [sum(int(l["candidatos"]) for l in linhas if l["escola"] == e and l["tipo"] == tipo)
                    for e in escolas]
            ax.bar(range(len(escolas)), vals, bottom=base, width=0.72, color=SERIE[t],
                   label=tipo if K == 1 else None, edgecolor=FUNDO, linewidth=1)
            base = [b + v for b, v in zip(base, vals)]
        caps = [sum(int(l["capacidade"]) for l in linhas if l["escola"] == e) for e in escolas]
        ax.scatter(range(len(escolas)), caps, marker="_", s=120, color=TXT1, linewidth=1.2,
                   label="capacidade" if K == 1 else None, zorder=4)
        ax.set_xticks(range(len(escolas)), escolas, fontsize=7)
        ax.grid(axis="x", visible=False)
        ax.set_ylabel("candidatos")
        ax.set_ylim(0, max(caps) * 1.08)
        ax.set_title(ROT_K[K], fontsize=8.5, color=TXT1, loc="left")
    fig.legend(ncol=7, fontsize=7, loc="lower center", bbox_to_anchor=(0.5, 1.0), handlelength=1.2,
               columnspacing=1.0)
    fig.tight_layout()
    salvar(fig, "distribuicao")


# ----------------------------------------------------------------------------- tabelas
def escrever(nome, linhas):
    (TAB / nome).write_text("\n".join(linhas) + "\n")


def tab_instancias(todas):
    l = [r"\begin{tabular}{llrrrrcc}", r"\hline",
         r" & & & & & & \multicolumn{2}{c}{Viável com} \\",
         r"ID & Arquivo & $M$ & $N$ & Salas & Folga (\%) & 1 tipo & 2 tipos \\", r"\hline"]
    for x in todas:
        pasta, arq = x["nome"].split("/", 1)
        marca = "$^\\ddagger$" if pasta == "instancias" else ""
        l.append(f"{x['id']} & \\texttt{{{tex_esc(arq)}}}{marca} & {x['M']} & {x['N']} & {x['salas']} & "
                 f"{br(x['folga'], 1)} & {'sim' if x[1] else 'não'} & {'sim' if x[2] else 'não'} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("instancias.tex", l)


def tab_resultados(todas, K, arquivo):
    l = [r"\begin{tabular}{lrrrrrrrr}", r"\hline",
         r" & \multicolumn{4}{c}{Construtivo (10 execuções)} & \multicolumn{4}{c}{Após o VND (10 execuções)} \\",
         r"ID & média & desvio & melhor & pior & média & desvio & melhor & pior \\", r"\hline"]
    for x in viaveis(todas, K):
        r = x[K]["r"]
        l.append(f"{x['id']} & " + " & ".join(
            br(f(r[c])) for c in ("inicial_media", "inicial_dp", "inicial_melhor", "inicial_pior",
                                  "final_media", "final_dp", "final_melhor", "final_pior")) + r" \\")
    l += [r"\hline", r"\end{tabular}"]
    escrever(arquivo, l)


def tab_qualidade(todas):
    """Por instância e por K: melhoria, gaps (inicial, final, LB) e tempo médio."""
    l = [r"\begin{tabular}{l rrrrr rrrrr}", r"\hline",
         r" & \multicolumn{5}{c}{1 tipo por escola} & \multicolumn{5}{c}{Até 2 tipos por escola} \\",
         r"ID & Melh. & Gap ini. & Gap fin. & Gap LB & $t$ & Melh. & Gap ini. & Gap fin. & Gap LB & $t$ \\",
         r" & (\%) & (\%) & (\%) & (\%) & (s) & (\%) & (\%) & (\%) & (\%) & (s) \\", r"\hline"]

    def cols(d):
        if not d:
            return r"\multicolumn{5}{c}{inviável}"
        marca = "$^*$" if d["ref_otima"] else ""
        return (f"{br(f(d['r']['melhoria_media_pct']))} & {br(d['gap_ini'])} & {br(d['gap_fin'])}{marca} & "
                f"{br(d['gap_lb'])} & {br(f(d['r']['t_total_medio']))}")

    for x in todas:
        if x[1] or x[2]:
            l.append(f"{x['id']} & {cols(x[1])} & {cols(x[2])} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("qualidade.tex", l)


def tab_vizinhancas(todas):
    """Movimentos, ganho e participação de cada vizinhança, para cada K."""
    l = [r"\begin{tabular}{lrrrrrr}", r"\hline",
         r" & \multicolumn{3}{c}{1 tipo por escola} & \multicolumn{3}{c}{Até 2 tipos por escola} \\",
         r"Vizinhança & Movs. & Ganho & \% da melhoria & Movs. & Ganho & \% da melhoria \\", r"\hline"]

    def cols(K, v):
        xs = viaveis(todas, K)
        movs = st.mean(st.mean(f(e.get(f"movs_{v}") or 0) for e in x[K]["execs"]) for x in xs)
        ganho = st.mean(100 * st.mean(f(e.get(f"ganho_{v}") or 0) for e in x[K]["execs"]) / x[K]["ini_media"]
                        for x in xs)
        return f"{br(movs, 1)} & {br(ganho, 2)}\\% & {br(participacao(xs, v, K), 1)}"

    for v, rot in zip(VIZ, VIZ_ROT):
        l.append(f"{rot} & {cols(1, v)} & {cols(2, v)} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("vizinhancas.tex", l)


def tab_tipos_por_escola(todas):
    """Comparação por instância: melhor valor, redução, gaps até o LB de transporte, escolas com
    dois tipos e escolas usadas."""
    l = [r"\begin{tabular}{lrrrrrcc}", r"\hline",
         r" & \multicolumn{2}{c}{Melhor valor} & Redução & \multicolumn{2}{c}{Gap até o LB (\%)} & "
         r"Escolas com & Escolas \\",
         r"ID & 1 tipo & 2 tipos & (\%) & 1 tipo & 2 tipos & 2 tipos & usadas \\", r"\hline"]
    for x in viaveis(todas, 2):
        d1, d2 = x[1], x[2]
        um, red, gap1 = (br(d1["fin_melhor"]), br(x["reducao"]), br(d1["gap_transp"])) if d1 else \
            ("inviável", "--", "--")
        usadas = d2["r"]["escolas_usadas_melhor"]
        l.append(f"{x['id']} & {um} & {br(d2['fin_melhor'])} & {red} & {gap1} & {br(d2['gap_transp'])} & "
                 f"{d2['duas']}/{x['N']} & {usadas}/{x['N']} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("tipos_por_escola.tex", l)


def sensibilidade(todas):
    """Gap médio (inicial e final) e coeficiente de variação para cada k (um tipo por escola)."""
    ref = {x["nome"]: x[1] for x in viaveis(todas, 1)}
    lin = []
    for k in KS:
        arq = RES[1] / "resumo.csv" if k == 10 else RES[1] / "sensibilidade_k" / f"k{k}" / "resumo.csv"
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


def resumo_escolas(K, nome):
    """{escola: (tipos, capacidade, candidatos, dist_media)} da melhor solução."""
    res = {}
    for l in ler(RES[K] / "solucoes" / f"{nome}_distribuicao.csv"):
        t, c, n, d = res.get(l["escola"], ([], 0, 0, 0.0))
        cap, cand = int(l["capacidade"]), int(l["candidatos"])
        res[l["escola"]] = (t + ([l["tipo"]] if cap > 0 else []), c + cap, n + cand,
                            d + cand * f(l["dist_media"]))
    return res


def tab_distribuicao(nome):
    """Resumo por escola da melhor solução (tipos, candidatos, ocupação e distância média), por K."""
    I = ler_instancia(RAIZ / f"{nome}.txt")
    r1, r2 = resumo_escolas(1, nome), resumo_escolas(2, nome)
    l = [r"\begin{tabular}{lr lrrr lrrr}", r"\hline",
         r" & & \multicolumn{4}{c}{1 tipo por escola} & \multicolumn{4}{c}{Até 2 tipos por escola} \\",
         r"Escola & Cap. & Tipo & Cand. & Ocup. (\%) & Dist. & Tipos & Cand. & Ocup. (\%) & Dist. \\", r"\hline"]
    for j, e in enumerate(I.escolas):
        cap = int(I.cap[j])
        cols = []
        for r in (r1, r2):
            t, _, n, d = r.get(e.id, ([], 0, 0, 0.0))
            cols.append(f"{'+'.join(t) or '--'} & {n} & {br(100 * n / cap, 1)} & {br(d / n if n else 0, 3)}")
        l.append(f"{e.id} & {cap} & {cols[0]} & {cols[1]} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("distribuicao.tex", l)


# ----------------------------------------------------------------------------- métricas
def piores(xs, K, n=3):
    return sorted(xs, key=lambda x: -x[K]["gap_fin"])[:n]


def metricas(todas, lin):
    m = {}
    por_nome = {x["nome"]: x for x in todas}
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
    inv1 = [x for x in todas if not x[1] and x[2]]
    m["nSoDois"] = str(len(inv1))
    m["soDois"] = ", ".join(x["id"] for x in inv1)
    m["soDoisNmin"] = str(min(x["N"] for x in inv1))
    m["nInviavelAmbos"] = str(sum(1 for x in todas if not x[1] and not x[2]))
    # métricas por K: sufixo Um (1 tipo por escola) ou Dois (até 2 tipos)
    for K, s in ((1, "Um"), (2, "Dois")):
        xs = viaveis(todas, K)
        g = lambda c: [x[K][c] for x in xs]
        m[f"nInst{s}"] = str(len(xs))
        m[f"nExec{s}"] = str(sum(len(x[K]["execs"]) for x in xs))
        m[f"gapIni{s}"] = br(st.mean(g("gap_ini")))
        m[f"gapFin{s}"] = br(st.mean(g("gap_fin")))
        m[f"gapLb{s}"] = br(st.mean(g("gap_lb")))
        m[f"melhoria{s}"] = br(st.mean(f(x[K]["r"]["melhoria_media_pct"]) for x in xs))
        m[f"refOtima{s}"] = str(sum(1 for x in xs if x[K]["ref_otima"]))
        m[f"otimos{s}"] = str(sum(1 for x in xs if x[K]["ref_otima"] and x[K]["gap_fin"] < 1e-3))
        m[f"abaixoUm{s}"] = str(sum(1 for x in xs if x[K]["gap_fin"] < 1))
        m[f"acimaCinco{s}"] = str(sum(1 for x in xs if x[K]["gap_fin"] >= 5))
        m[f"refHeur{s}"] = str(sum(1 for x in xs if abs(x[K]["fin_melhor"] - x[K]["ref"]) < 1e-6
                                    and not x[K]["ref_otima"]))
        m[f"melhorQueMip{s}"] = str(sum(1 for x in xs if x[K]["mip"] and x[K]["fin_melhor"] < x[K]["mip"] - 1e-6))
        m[f"semMip{s}"] = str(sum(1 for x in xs if not x[K]["mip"]))
        m[f"tempoMedio{s}"] = br(st.mean(f(x[K]["r"]["t_total_medio"]) for x in xs), 2)
        lenta = max(xs, key=lambda x: f(x[K]["r"]["t_total_medio"]))
        m[f"tempoMax{s}"], m[f"tempoMaxId{s}"] = br(f(lenta[K]["r"]["t_total_medio"]), 2), lenta["id"]
        m[f"tConstrMax{s}"] = br(max(f(x[K]["r"]["t_construtivo_medio"]) for x in xs), 3)
        m[f"cvIni{s}"] = br(st.mean(100 * f(x[K]["r"]["inicial_dp"]) / f(x[K]["r"]["inicial_media"]) for x in xs), 3)
        m[f"cvIniMax{s}"] = br(max(100 * f(x[K]["r"]["inicial_dp"]) / f(x[K]["r"]["inicial_media"]) for x in xs), 3)
        m[f"cvFinMax{s}"] = br(max(100 * f(x[K]["r"]["final_dp"]) / f(x[K]["r"]["final_media"]) for x in xs), 3)
        m[f"nVariaFin{s}"] = str(sum(1 for x in xs if f(x[K]["r"]["final_dp"]) > 1e-6))
        for n, x in enumerate(piores(xs, K), 1):
            p = ["Um", "Dois", "Tres"][n - 1]
            m[f"pior{p}Id{s}"], m[f"pior{p}Gap{s}"] = x["id"], br(x[K]["gap_fin"], 1)
            m[f"pior{p}N{s}"], m[f"pior{p}M{s}"] = str(x["N"]), str(x["M"])
        ret = [max(int(e["retipagens_faseA"]) for e in x[K]["execs"]) for x in xs]
        m[f"coberturaInst{s}"] = str(sum(1 for r in ret if r > 0))
        rep = [x for x in xs if any(e["reparo_faseA"] == "1" for e in x[K]["execs"])]
        m[f"reparoInst{s}"] = str(len(rep))
        m[f"reparoIds{s}"] = ", ".join(x["id"] for x in rep) if rep else "nenhuma"
        for v in VIZ:
            nome_v = {"N1_shift": "NUm", "N2_swap": "NDois", "N3_cadeias": "NTres", "N4_retipar": "NQuatro",
                      "N5_trocar": "NCinco", "N6_escola": "NSeis", "N7_trocar_escolas": "NSete"}[v]
            m[f"part{nome_v}{s}"] = br(participacao(xs, v, K), 1)
        ex = [(e, x) for x in xs for e in x[K]["execs"]]
        tb = [f(e["t_busca"]) for e, _ in ex]
        m[f"corrTempoM{s}"] = br(st.correlation(tb, [x["M"] for _, x in ex]))
        m[f"corrTempoTipos{s}"] = br(st.correlation(
            tb, [sum(f(e[f"movs_{v}"]) for v in VIZ[3:]) for e, _ in ex]))
        fech = [x for x in xs if int(x[K]["r"]["escolas_usadas_melhor"]) < x["N"]]
        m[f"nFechou{s}"] = str(len(fech))
    # busca exata nos tipos (K = 1): quanto ela melhora a melhor solução da heurística
    bt = [(x, 100 * (x[1]["fin_melhor"] - x[1]["btipos"]) / x[1]["fin_melhor"]) for x in viaveis(todas, 1)]
    m["nBuscaTipos"] = str(sum(1 for _, g in bt if g > 1e-6))
    m["nBuscaTiposUm"] = str(sum(1 for _, g in bt if g >= 1))
    m["buscaTiposMedia"] = br(st.mean(g for _, g in bt))
    xb, gb = max(bt, key=lambda p: p[1])
    m["buscaTiposMax"], m["buscaTiposMaxId"] = br(gb, 1), xb["id"]
    # comparação entre K = 1 e K = 2
    comp = [x for x in todas if x[1] and x[2]]
    m["nComp"] = str(len(comp))
    m["reducao"] = br(st.mean(x["reducao"] for x in comp), 1)
    rmin, rmax = min(comp, key=lambda x: x["reducao"]), max(comp, key=lambda x: x["reducao"])
    m["reducaoMin"], m["reducaoMinId"] = br(rmin["reducao"], 1), rmin["id"]
    m["reducaoMax"], m["reducaoMaxId"] = br(rmax["reducao"], 1), rmax["id"]
    m["nPiora"] = str(sum(1 for x in comp if x["reducao"] < -1e-9))
    m["nReducaoCinco"] = str(sum(1 for x in comp if x["reducao"] >= 5))
    m["gapTranspUm"] = br(st.mean(x[1]["gap_transp"] for x in comp))
    m["gapTranspDois"] = br(st.mean(x[2]["gap_transp"] for x in comp))
    m["fechado"] = br(st.mean(x["fechado"] for x in comp), 1)
    duas = [100 * x[2]["duas"] / x["N"] for x in viaveis(todas, 2)]
    m["duasMedia"] = br(st.mean(duas), 1)
    m["duasMin"], m["duasMax"] = br(min(duas), 0), br(max(duas), 0)
    # instâncias citadas: valores e gaps
    for k, nome in CITADAS.items():
        x, suf = por_nome[nome], k[2:]
        for K, s in ((1, "Um"), (2, "Dois")):
            if x[K]:
                m[f"final{suf}{s}"] = br(x[K]["fin_melhor"])
                m[f"ref{suf}{s}"] = br(x[K]["ref"])
                m[f"gap{suf}{s}"] = br(x[K]["gap_fin"], 1)
                m[f"duas{suf}"] = str(x[2]["duas"]) if x[2] else "--"
        if x[1] and x[2]:
            m[f"reducao{suf}"] = br(x["reducao"], 1)
    linhas = ["% gerado por relatorio/gerar_figuras.py -- não editar"]
    linhas += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in m.items()]
    escrever("metricas.tex", linhas)
    return m


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    for antiga in FIG.glob("*.pdf"):        # versões antigas das figuras em PDF
        antiga.unlink()
    for antiga in ("modelos.png", "tipos_por_sala.png"):
        (FIG / antiga).unlink(missing_ok=True)
    for antiga in ("tipos_por_sala.tex",):
        (TAB / antiga).unlink(missing_ok=True)
    todas = carregar()
    lin = sensibilidade(todas)
    fig_gaps(todas)
    fig_vizinhancas(todas)
    fig_tempo(todas)
    fig_variabilidade(todas)
    fig_tipos_por_escola(todas)
    fig_distribuicao(CITADAS["idGrupo"])
    tab_instancias(todas)
    tab_resultados(todas, 1, "resultados.tex")
    tab_resultados(todas, 2, "resultados_tipos2.tex")
    tab_qualidade(todas)
    tab_vizinhancas(todas)
    tab_tipos_por_escola(todas)
    tab_sensibilidade(lin)
    tab_distribuicao(CITADAS["idGrupo"])
    m = metricas(todas, lin)
    for k, v in m.items():
        print(f"{k:22s} {v}")
    print(f"k testados: {[l['k'] for l in lin]}")


if __name__ == "__main__":
    main()
