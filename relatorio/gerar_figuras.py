"""Gera as figuras (PNG, 300 dpi), as tabelas (LaTeX) e as métricas (macros LaTeX) do relatório a
partir dos resultados dos experimentos e das análises. As figuras são sempre imagens, nunca PDF.

Entradas:
  resultados/resumo.csv, resultados/execucoes.csv     experimento principal (k = 10, 10 execuções,
                                                      um tipo por sala)
  resultados/tipos2/resumo.csv, .../execucoes.csv     mesmo experimento com até dois tipos por sala
  resultados/tipos2/solucoes/<inst>.txt               salas divididas na melhor solução (2 tipos)
  resultados/sensibilidade_k/k*/resumo.csv            sensibilidade ao tamanho da RCL
  resultados/solucoes/instancias/instancia_1_distribuicao.csv   distribuição (exemplo)
  analise/resultados/caracteristicas.csv              características das instâncias
  analise/resultados/modelo_sala.csv                  viabilidade, limite inferior e MIP (um tipo por sala)
  analise/resultados/modelo_escola.csv                melhor valor com um tipo por escola
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
sys.path.insert(0, str(RAIZ / "analise"))
from instancia import ler_instancia  # noqa: E402
from modelo_sala import limite_inferior  # noqa: E402

RES = RAIZ / "resultados"
RES2 = RES / "tipos2"
ANA = RAIZ / "analise" / "resultados"
FIG = Path(__file__).parent / "figuras"
TAB = Path(__file__).parent / "tabelas"

# paleta categórica validada (ordem fixa) e tokens de texto/grade
SERIE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
TXT1, TXT2, GRADE, FUNDO = "#0b0b0b", "#52514e", "#e6e5e0", "#ffffff"
TIPOS = ["M1", "M2", "M3e", "M3s", "M3h", "M3d"]
VIZ = ["N1_shift", "N2_swap", "N3_cadeias", "N4_retipar", "N5_trocar", "N6_dividir"]
VIZ_ROT = ["N1 shift", "N2 swap", "N3 cadeias", "N4 retipar", "N5 trocar", "N6 dividir"]
KS = [1, 5, 10, 25, 50]
# instâncias citadas no texto do relatório (macro LaTeX -> caminho relativo sem .txt)
CITADAS = {
    "idExemplo": "instancias_pism/instancia1_G8",       # exemplo passo a passo
    "idInstUm": "instancias_pism/instancia_1_G13",       # casos ruins (poucas salas pequenas)
    "idInstDois": "instancias_pism/instancia_2_G13",
    "idDoisUmUm": "instancias_pism/instancia_2_G14",
    "idGrupo": "instancias/instancia_1",                  # instância do grupo (distribuição)
    "idInviavel": "instancias_pism/Instancia1_G2",        # inviável mesmo por sala
    "idLenta": "instancias_pism/Instancia1_G6",           # mais lenta
    "idFechou": "instancias_pism/Instancia2_G11",         # deixa escolas fechadas
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
def salas_divididas(nome):
    """Salas com dois tipos na melhor solução com até dois tipos por sala."""
    sol = open(RES2 / "solucoes" / f"{nome}.txt").read().splitlines()
    ini = sol.index("# SALAS (escola, sala, capacidade, tipo, ocupacao)") + 1
    return sum(1 for l in sol[ini:] if not l.startswith("#") and "+" in l.split(",")[3])


def carregar():
    resumo = ler(RES / "resumo.csv")
    execs = ler(RES / "execucoes.csv")
    resumo2 = {r["instancia"]: r for r in ler(RES2 / "resumo.csv")}
    execs2 = ler(RES2 / "execucoes.csv")
    sal = {r["instancia"]: r for r in ler(ANA / "modelo_sala.csv")}
    esc = {r["instancia"]: r for r in ler(ANA / "modelo_escola.csv")}
    inst = []
    for r in resumo:
        nome, s = r["instancia"], sal[r["instancia"]]
        # melhor valor conhecido: MIP, alocação ótima com os tipos da fase A ou a própria heurística
        ref = min(x for x in (f(s["MIP"]), f(s["aloc_otima"]), f(r["final_melhor"])) if x)
        I = ler_instancia(RAIZ / f"{nome}.txt")
        inst.append({
            "nome": nome, "M": I.M, "N": I.N, "salas": I.num_salas,
            "folga": 100 * (I.cap.sum() - I.M) / I.M,
            "ref": ref, "lb": max(f(s["LB"]), f(s["MIP_lb"]) or 0), "ref_otima": s["MIP_otimo"] == "1",
            "lb_transp": f(s["LB"]),
            "mip_sala": f(s["MIP"]), "por_escola": f(esc[nome]["melhor"]),
            "r": r, "execs": [e for e in execs if e["instancia"] == nome],
        })
    inst.sort(key=lambda x: (x["M"], x["nome"]))
    # instâncias sem solução: aparecem só na tabela de instâncias, com os últimos IDs
    inviaveis = []
    for nome, s in sal.items():
        if s["viavel"] == "0":
            I = ler_instancia(RAIZ / f"{nome}.txt")
            inviaveis.append({"nome": nome, "M": I.M, "N": I.N, "salas": I.num_salas,
                              "folga": 100 * (I.cap.sum() - I.M) / I.M, "inviavel": True})
    for k, x in enumerate(inst, 1):
        x["id"] = f"I{k:02d}"
        r = x["r"]
        x["ini_media"], x["fin_melhor"] = f(r["inicial_media"]), f(r["final_melhor"])
        x["gap_ini"] = 100 * (x["ini_media"] - x["ref"]) / x["ref"]
        x["gap_fin"] = 100 * (x["fin_melhor"] - x["ref"]) / x["ref"]
        x["gap_lb"] = 100 * (x["fin_melhor"] - x["lb"]) / x["lb"]
    for k, x in enumerate(sorted(inviaveis, key=lambda x: x["M"]), len(inst) + 1):
        x["id"] = f"I{k:02d}"
    # até dois tipos por sala: todas as instâncias (inclusive as inviáveis com um tipo por sala).
    # Referência comum aos dois modelos: só o LB de transporte (MIP_lb vale só para um tipo por sala).
    for x in inst + inviaveis:
        nome = x["nome"]
        x["r2"] = resumo2.get(nome)
        x["execs2"] = [e for e in execs2 if e["instancia"] == nome]
        if x["r2"] is None:
            continue
        if x.get("inviavel"):           # sem LB no modelo_sala.csv: calcula a mesma relaxação
            x["lb_transp"] = limite_inferior(ler_instancia(RAIZ / f"{nome}.txt"))
        lb = x["lb_transp"]
        x["fin2"] = f(x["r2"]["final_melhor"])
        x["gap_lb2"] = 100 * (x["fin2"] - lb) / lb
        x["divididas"] = salas_divididas(nome)
        if not x.get("inviavel"):
            x["gap_lb1"] = 100 * (x["fin_melhor"] - lb) / lb
            x["reducao2"] = 100 * (x["fin_melhor"] - x["fin2"]) / x["fin_melhor"]
            # fração do intervalo [LB, valor com um tipo] eliminada ao permitir dois tipos
            x["fechado2"] = 100 * (x["fin_melhor"] - x["fin2"]) / (x["fin_melhor"] - lb) \
                if x["fin_melhor"] - lb > 1e-9 else 0.0
    return inst, inviaveis


# ----------------------------------------------------------------------------- figuras
def fig_gaps(inst):
    """Gap até o melhor valor conhecido: solução inicial (média) e após o VND."""
    xs = sorted(inst, key=lambda x: x["gap_fin"])
    fig, ax = plt.subplots(figsize=(LARG, 0.17 * len(xs) + 1.0))
    y = range(len(xs))
    for i, x in zip(y, xs):
        ax.plot([x["gap_fin"], x["gap_ini"]], [i, i], color=GRADE, lw=1.5, zorder=1)
    ax.scatter([x["gap_ini"] for x in xs], y, s=26, color=SERIE[1], zorder=3, label="construtivo (média)",
               edgecolor=FUNDO, linewidth=1)
    ax.scatter([x["gap_fin"] for x in xs], y, s=26, color=SERIE[0], zorder=3, label="após o VND",
               edgecolor=FUNDO, linewidth=1)
    ax.set_yticks(list(y), [x["id"] for x in xs], fontsize=7)
    ax.set_ylim(-0.8, len(xs) - 0.2)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(FMT)
    ax.set_xlabel("gap até o melhor valor conhecido (%)")
    ax.set_xlim(left=-0.5)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=7.5, handletextpad=0.2)
    salvar(fig, "gaps")


def participacao(inst, v, execs="execs"):
    """Participação média (por instância) da vizinhança v na melhoria total."""
    vals = []
    for x in inst:
        tot = st.mean(f(e["melhoria"]) for e in x[execs])
        vals.append(100 * st.mean(f(e.get(f"ganho_{v}") or 0) for e in x[execs]) / tot if tot > 0 else 0)
    return st.mean(vals)


def fig_vizinhancas(inst, todas):
    """Participação de cada vizinhança na melhoria total (média por instância), com um e com até
    dois tipos por sala (N6 só existe com dois)."""
    fig, ax = plt.subplots(figsize=(LARG, 2.3))
    larg = 0.38
    series = [("1 tipo por sala", [participacao(inst, v) for v in VIZ[:5]], SERIE[0], -larg / 2),
              ("até 2 tipos por sala", [participacao(todas, v, "execs2") for v in VIZ], SERIE[2], larg / 2)]
    for rot, part, cor, desl in series:
        pos = [p + desl for p in range(len(part))]
        ax.bar(pos, part, width=larg, color=cor, edgecolor=FUNDO, linewidth=1, label=rot)
        for p, v in zip(pos, part):
            ax.text(p, v + 1.5, br(v, 1), ha="center", fontsize=6.5, color=TXT2)
    ax.set_xticks(range(len(VIZ)), VIZ_ROT)
    ax.set_ylabel("% da melhoria total")
    ax.yaxis.set_major_formatter(FMT)
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, 105)
    ax.legend(fontsize=7.5, loc="upper right")
    salvar(fig, "vizinhancas")


def fig_tempo(inst):
    """Tempo médio por execução (construtivo + VND) em função do número de candidatos."""
    fig, ax = plt.subplots(figsize=(LARG, 2.4))
    ax.scatter([x["M"] for x in inst], [f(x["r"]["t_total_medio"]) for x in inst], s=30, color=SERIE[0],
               edgecolor=FUNDO, linewidth=1, zorder=3)
    lento = max(inst, key=lambda x: f(x["r"]["t_total_medio"]))
    ax.annotate(f"{lento['id']}", (lento["M"], f(lento["r"]["t_total_medio"])), xytext=(6, -2),
                textcoords="offset points", fontsize=7, color=TXT2)
    ax.set_xlabel("número de candidatos (M)")
    ax.set_ylabel("tempo por execução (s)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: br_milhar(v, 0)))
    ax.yaxis.set_major_formatter(FMT)
    salvar(fig, "tempo")


def fig_variabilidade(inst):
    """Desvio de cada execução em relação à média da instância (valor inicial e final)."""
    xs = sorted(inst, key=lambda x: x["id"])
    fig, ax = plt.subplots(figsize=(LARG, 2.6))
    for k, x in enumerate(xs):
        ini = [f(e["valor_inicial"]) for e in x["execs"]]
        fin = [f(e["valor_final"]) for e in x["execs"]]
        m = st.mean(ini)
        ax.scatter([k - 0.15] * len(ini), [100 * (v - m) / m for v in ini], s=10, color=SERIE[1],
                   label="construtivo" if k == 0 else None, linewidth=0, alpha=0.85)
        mf = st.mean(fin)
        ax.scatter([k + 0.15] * len(fin), [100 * (v - mf) / mf for v in fin], s=10, color=SERIE[0],
                   label="após o VND" if k == 0 else None, linewidth=0)
    ax.axhline(0, color=TXT2, lw=0.6)
    ax.set_xticks(range(len(xs)), [x["id"] for x in xs], rotation=90, fontsize=6.5)
    ax.set_xlim(-0.8, len(xs) - 0.2)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("desvio da média (%)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: br(v, 2)))
    ax.legend(fontsize=7.5, loc="upper right", ncol=2)
    salvar(fig, "variabilidade")


def sensibilidade(inst):
    """Gap médio (inicial e final) e coeficiente de variação do inicial para cada k."""
    ref = {x["nome"]: x for x in inst}
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


def fig_modelos(inst):
    """Redução da distância total do modelo 'tipo por sala' em relação a 'tipo por escola'."""
    xs = [x for x in inst if x["por_escola"]]   # sem as inviáveis por escola
    for x in xs:
        x["reducao"] = 100 * (x["por_escola"] - x["fin_melhor"]) / x["por_escola"]
    xs.sort(key=lambda x: -x["reducao"])
    fig, ax = plt.subplots(figsize=(LARG, 2.5))
    pos = range(len(xs))
    ax.bar(list(pos), [x["reducao"] for x in xs], width=0.7, color=SERIE[0], edgecolor=FUNDO, linewidth=1)
    ax.axhline(0, color=TXT2, lw=0.6)
    ax.set_xticks(list(pos), [x["id"] for x in xs], rotation=90, fontsize=6.5)
    ax.set_xlim(-0.8, len(xs) - 0.2)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("redução da distância (%)")
    ax.yaxis.set_major_formatter(FMT)
    salvar(fig, "modelos")


def fig_tipos_por_sala(todas):
    """Gap até o limite inferior da melhor solução com um e com até dois tipos por sala."""
    xs = sorted((x for x in todas if x.get("r2")), key=lambda x: x["gap_lb2"])
    fig, ax = plt.subplots(figsize=(LARG, 0.17 * len(xs) + 1.0))
    y = list(range(len(xs)))
    for i, x in zip(y, xs):
        if not x.get("inviavel"):
            ax.plot([x["gap_lb2"], x["gap_lb1"]], [i, i], color=GRADE, lw=1.5, zorder=1)
    um = [(i, x["gap_lb1"]) for i, x in zip(y, xs) if not x.get("inviavel")]
    ax.scatter([g for _, g in um], [i for i, _ in um], s=26, color=SERIE[0], zorder=3,
               label="1 tipo por sala", edgecolor=FUNDO, linewidth=1)
    ax.scatter([x["gap_lb2"] for x in xs], y, s=26, color=SERIE[2], zorder=3, label="até 2 tipos por sala",
               edgecolor=FUNDO, linewidth=1)
    ax.set_yticks(y, [x["id"] + ("$^\\dagger$" if x.get("inviavel") else "") for x in xs], fontsize=7)
    ax.set_ylim(-0.8, len(xs) - 0.2)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(FMT)
    ax.set_xlabel("gap até o limite inferior de transporte (%)")
    ax.set_xlim(left=-0.5)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=7.5, handletextpad=0.2)
    salvar(fig, "tipos_por_sala")


def fig_distribuicao(nome):
    """Candidatos por escola e tipo de prova na melhor solução de uma instância."""
    arq = RES / "solucoes" / f"{nome}_distribuicao.csv"
    linhas = ler(arq)
    escolas = list(dict.fromkeys(l["escola"] for l in linhas))
    fig, ax = plt.subplots(figsize=(LARG, 2.6))
    base = [0] * len(escolas)
    for t, tipo in enumerate(TIPOS):
        vals = [sum(int(l["candidatos"]) for l in linhas if l["escola"] == e and l["tipo"] == tipo) for e in escolas]
        ax.bar(range(len(escolas)), vals, bottom=base, width=0.72, color=SERIE[t], label=tipo,
               edgecolor=FUNDO, linewidth=1)
        base = [b + v for b, v in zip(base, vals)]
    caps = [sum(int(l["capacidade"]) for l in linhas if l["escola"] == e) for e in escolas]
    ax.scatter(range(len(escolas)), caps, marker="_", s=120, color=TXT1, linewidth=1.2, label="capacidade", zorder=4)
    ax.set_xticks(range(len(escolas)), escolas, fontsize=7)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("candidatos")
    ax.set_ylim(0, max(caps) * 1.05)
    ax.legend(ncol=7, fontsize=7, loc="lower center", bbox_to_anchor=(0.5, 1.02), handlelength=1.2,
              columnspacing=1.0)
    salvar(fig, "distribuicao")


# ----------------------------------------------------------------------------- tabelas
def escrever(nome, linhas):
    (TAB / nome).write_text("\n".join(linhas) + "\n")


def tab_instancias(inst, inviaveis):
    l = [r"\begin{tabular}{llrrrrl}", r"\hline",
         r"ID & Arquivo & $M$ & $N$ & Salas & Folga (\%) & Observação \\", r"\hline"]
    for x in inst + inviaveis:
        pasta, arq = x["nome"].split("/", 1)
        obs = "inviável" if x.get("inviavel") else ("cópia do G3; pasta \\texttt{instancias}" if pasta == "instancias" else "")
        l.append(f"{x['id']} & \\texttt{{{tex_esc(arq)}}} & "
                 f"{x['M']} & {x['N']} & {x['salas']} & {br(x['folga'], 1)} & {obs} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("instancias.tex", l)


def tab_resultados(inst, chave="r", arquivo="resultados.tex"):
    l = [r"\begin{tabular}{lrrrrrrrr}", r"\hline",
         r" & \multicolumn{4}{c}{Construtivo (10 execuções)} & \multicolumn{4}{c}{Após o VND (10 execuções)} \\",
         r"ID & média & desvio & melhor & pior & média & desvio & melhor & pior \\", r"\hline"]
    for x in inst:
        r = x[chave]
        d = 2
        l.append(f"{x['id']} & " + " & ".join(
            br(f(r[c]), d) for c in ("inicial_media", "inicial_dp", "inicial_melhor", "inicial_pior",
                                     "final_media", "final_dp", "final_melhor", "final_pior")) + r" \\")
    l += [r"\hline", r"\end{tabular}"]
    escrever(arquivo, l)


def tab_qualidade(inst):
    l = [r"\begin{tabular}{lrrrrrrrr}", r"\hline",
         r"ID & Melhoria & Gap ini. & Gap final & Gap LB & $t_c$ & $t_{bl}$ & Escolas & Salas \\",
         r" & (\%) & (\%) & (\%) & (\%) & (s) & (s) & usadas & usadas \\", r"\hline"]
    for x in inst:
        r = x["r"]
        marca = "$^*$" if x["ref_otima"] else ""
        l.append(f"{x['id']} & {br(f(r['melhoria_media_pct']))} & {br(x['gap_ini'])} & {br(x['gap_fin'])}{marca} & "
                 f"{br(x['gap_lb'])} & {br(f(r['t_construtivo_medio']), 3)} & {br(f(r['t_busca_medio']), 2)} & "
                 f"{r['escolas_usadas_melhor']}/{x['N']} & {r['salas_usadas_melhor']}/{x['salas']} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("qualidade.tex", l)


def tab_vizinhancas(inst, todas):
    """Movimentos, ganho e participação de cada vizinhança, com um e com até dois tipos por sala."""
    l = [r"\begin{tabular}{lrrrrrr}", r"\hline",
         r" & \multicolumn{3}{c}{1 tipo por sala} & \multicolumn{3}{c}{Até 2 tipos por sala} \\",
         r"Vizinhança & Movs. & Ganho & \% da melhoria & Movs. & Ganho & \% da melhoria \\", r"\hline"]

    def cols(xs, v, execs, r):
        movs = st.mean(st.mean(f(e.get(f"movs_{v}") or 0) for e in x[execs]) for x in xs)
        ganho = st.mean(100 * st.mean(f(e.get(f"ganho_{v}") or 0) for e in x[execs]) / f(x[r]["inicial_media"])
                        for x in xs)
        return f"{br(movs, 1)} & {br(ganho, 2)}\\% & {br(participacao(xs, v, execs), 1)}"

    for k, (v, rot) in enumerate(zip(VIZ, VIZ_ROT)):
        um = cols(inst, v, "execs", "r") if k < 5 else "-- & -- & --"
        l.append(f"{rot} & {um} & {cols(todas, v, 'execs2', 'r2')} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("vizinhancas.tex", l)


def tab_tipos_por_sala(todas):
    """Comparação por instância: melhor valor, redução, gaps até o LB, salas divididas e tempo."""
    l = [r"\begin{tabular}{lrrrrrrrr}", r"\hline",
         r" & \multicolumn{2}{c}{Melhor valor} & Redução & \multicolumn{2}{c}{Gap até o LB (\%)} & Salas "
         r"& \multicolumn{2}{c}{Tempo médio (s)} \\",
         r"ID & 1 tipo & 2 tipos & (\%) & 1 tipo & 2 tipos & divididas & 1 tipo & 2 tipos \\", r"\hline"]
    for x in todas:
        if not x.get("r2"):
            continue
        if x.get("inviavel"):
            um, red, gap1, t1 = "inviável", "--", "--", "--"
        else:
            um, red = br(x["fin_melhor"]), br(x["reducao2"])
            gap1, t1 = br(x["gap_lb1"]), br(f(x["r"]["t_total_medio"]))
        l.append(f"{x['id']} & {um} & {br(x['fin2'])} & {red} & {gap1} & {br(x['gap_lb2'])} & "
                 f"{x['divididas']}/{x['salas']} & {t1} & {br(f(x['r2']['t_total_medio']))} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("tipos_por_sala.tex", l)


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
    """Resumo por escola da melhor solução: salas usadas, tipos atendidos, ocupação, distância."""
    sol = open(RES / "solucoes" / f"{nome}.txt").read().splitlines()
    salas = {}
    for l in sol[sol.index("# SALAS (escola, sala, capacidade, tipo, ocupacao)") + 1:]:
        if l.startswith("#"):
            break
        e, _, cap, tipo, oc = [c.strip() for c in l.split(",")]
        salas.setdefault(e, []).append((int(cap), tipo, int(oc)))
    dist = {}
    for x in ler(RES / "solucoes" / f"{nome}_distribuicao.csv"):
        dist.setdefault(x["escola"], []).append((int(x["candidatos"]), f(x["dist_media"]), x["tipo"]))
    l = [r"\begin{tabular}{lrrrrrr}", r"\hline",
         r"Escola & Salas usadas & Tipos & Capacidade & Candidatos & Ocupação (\%) & Dist. média \\", r"\hline"]
    for e, ss in salas.items():
        cap = sum(c for c, _, _ in ss)
        cand = sum(o for _, _, o in ss)
        usadas = sum(1 for _, _, o in ss if o > 0)
        tipos = len({t for n, _, t in dist.get(e, []) if n > 0})
        dm = sum(n * d for n, d, _ in dist.get(e, [])) / cand if cand else 0
        l.append(f"{e} & {usadas}/{len(ss)} & {tipos} & {cap} & {cand} & {br(100 * cand / cap, 1)} & {br(dm, 3)} \\\\")
    l += [r"\hline", r"\end{tabular}"]
    escrever("distribuicao.tex", l)


# ----------------------------------------------------------------------------- métricas
def metricas(inst, inviaveis, lin):
    m = {}
    m["nInst"] = str(len(inst))
    m["nInviaveis"] = str(len(inviaveis))
    m["nTotal"] = str(len(inst) + len(inviaveis))
    m["gapIni"] = br(st.mean(x["gap_ini"] for x in inst))
    m["gapFin"] = br(st.mean(x["gap_fin"] for x in inst))
    m["gapFinMax"] = br(max(x["gap_fin"] for x in inst))
    m["gapLb"] = br(st.mean(x["gap_lb"] for x in inst))
    m["melhoria"] = br(st.mean(f(x["r"]["melhoria_media_pct"]) for x in inst))
    m["tempoMedio"] = br(st.mean(f(x["r"]["t_total_medio"]) for x in inst), 2)
    m["otimos"] = str(sum(1 for x in inst if abs(x["gap_fin"]) < 1e-3 and x["ref_otima"]))
    m["refOtima"] = str(sum(1 for x in inst if x["ref_otima"]))
    m["abaixoUm"] = str(sum(1 for x in inst if x["gap_fin"] < 1))
    m["melhorQueMip"] = str(sum(1 for x in inst if x["mip_sala"] and x["fin_melhor"] < x["mip_sala"] - 1e-6))
    m["semMip"] = str(sum(1 for x in inst if not x["mip_sala"]))
    red = [100 * (x["por_escola"] - x["fin_melhor"]) / x["por_escola"] for x in inst if x["por_escola"]]
    m["nComparaModelo"] = str(len(red))
    m["reducaoModelo"] = br(st.mean(red), 1)
    m["reducaoModeloMin"] = br(min(red), 1)
    m["reducaoModeloMax"] = br(max(red), 1)
    m["tempoMax"] = br(max(f(x["r"]["t_total_medio"]) for x in inst), 2)
    m["tempoMaxId"] = max(inst, key=lambda x: f(x["r"]["t_total_medio"]))["id"]
    m["tConstrMax"] = br(max(f(x["r"]["t_construtivo_medio"]) for x in inst), 3)
    m["cvIni"] = br(st.mean(100 * f(x["r"]["inicial_dp"]) / f(x["r"]["inicial_media"]) for x in inst), 3)
    m["cvIniMax"] = br(max(100 * f(x["r"]["inicial_dp"]) / f(x["r"]["inicial_media"]) for x in inst), 3)
    m["cvFinMax"] = br(max(100 * f(x["r"]["final_dp"]) / f(x["r"]["final_media"]) for x in inst), 3)
    m["nExec"] = str(sum(len(x["execs"]) for x in inst))
    pior = max(inst, key=lambda x: x["gap_fin"])
    m["piorId"], m["piorGap"] = pior["id"], br(pior["gap_fin"])
    m["folgaMin"] = br(min(x["folga"] for x in inst + inviaveis), 1)
    m["folgaMax"] = br(max(x["folga"] for x in inst + inviaveis), 1)
    m["Mmin"] = str(min(x["M"] for x in inst + inviaveis))
    m["Mmax"] = str(max(x["M"] for x in inst + inviaveis))
    m["Nmin"] = str(min(x["N"] for x in inst + inviaveis))
    m["Nmax"] = str(max(x["N"] for x in inst + inviaveis))
    # caracterização (analise/resultados/caracteristicas.csv)
    car = ler(ANA / "caracteristicas.csv")
    m["fracSobreMin"] = br(100 * min(f(r["frac_sobrecarga"]) for r in car), 0)
    m["fracSobreMax"] = br(100 * max(f(r["frac_sobrecarga"]) for r in car), 0)
    m["sobrecargaMax"] = br(max(f(r["sobrecarga_max"]) for r in car), 1)
    # modelo por escola: instâncias inviáveis nele e viáveis por sala
    por_nome = {x["nome"]: x["id"] for x in inst + inviaveis}
    inv_esc = sorted(por_nome[r["instancia"]] for r in ler(ANA / "modelo_escola.csv")
                     if r["viavel"] == "0" and r["instancia"] in {x["nome"] for x in inst})
    m["nInviavelEscola"] = str(len(inv_esc))
    m["inviaveisEscola"] = ", ".join(inv_esc) if inv_esc else "nenhuma"
    pior_mod = min((x for x in inst if x["por_escola"]),
                   key=lambda x: (x["por_escola"] - x["fin_melhor"]) / x["por_escola"])
    m["reducaoModeloMinId"] = pior_mod["id"]
    for k, nome in CITADAS.items():
        m[k] = por_nome[nome]
    # gap final e referência das instâncias citadas (sufixo do nome da macro de ID)
    por_inst = {x["nome"]: x for x in inst}
    for k, nome in CITADAS.items():
        if nome in por_inst:
            x = por_inst[nome]
            suf = k[2:]
            m[f"gap{suf}"] = br(x["gap_fin"], 1)
            m[f"ref{suf}"] = br(x["ref"], 2)
            m[f"final{suf}"] = br(x["fin_melhor"], 2)
            if x["por_escola"]:
                m[f"reducao{suf}"] = br(100 * (x["por_escola"] - x["fin_melhor"]) / x["por_escola"], 1)
    # retipagens da etapa de cobertura (fase A)
    ret = [max(int(e["retipagens_faseA"]) for e in x["execs"]) for x in inst]
    m["coberturaInst"] = str(sum(1 for r in ret if r > 0))
    m["coberturaMax"] = str(max(ret))
    # tempo da busca x mudanças de tipo aceitas (N4 + N5) e x número de candidatos, por execução
    ex = [(e, x) for x in inst for e in x["execs"]]
    tb = [f(e["t_busca"]) for e, _ in ex]
    m["corrTempoTipos"] = br(st.correlation(tb, [f(e["movs_N4_retipar"]) + f(e["movs_N5_trocar"]) for e, _ in ex]))
    m["corrTempoM"] = br(st.correlation(tb, [x["M"] for _, x in ex]))
    lenta = max(inst, key=lambda x: f(x["r"]["t_total_medio"]))
    n4 = st.mean(f(e["movs_N4_retipar"]) for e in lenta["execs"])
    n5 = st.mean(f(e["movs_N5_trocar"]) for e in lenta["execs"])
    m["movsTiposLenta"], m["movsNQuatroLenta"], m["movsNCincoLenta"] = br(n4 + n5, 0), br(n4, 0), br(n5, 0)
    fechou = por_inst[CITADAS["idFechou"]]
    m["folgaFechou"] = br(fechou["folga"], 1)
    m["escolasFechadas"] = str(fechou["N"] - int(fechou["r"]["escolas_usadas_melhor"]))
    # até dois tipos por sala (resultados/tipos2)
    todas = [x for x in inst + inviaveis if x.get("r2")]
    comp = [x for x in todas if not x.get("inviavel")]
    m["nInstDois"] = str(len(todas))
    m["nExecDois"] = str(sum(len(x["execs2"]) for x in todas))
    m["reducaoDois"] = br(st.mean(x["reducao2"] for x in comp))
    rmin, rmax = min(comp, key=lambda x: x["reducao2"]), max(comp, key=lambda x: x["reducao2"])
    m["reducaoDoisMin"], m["reducaoDoisMinId"] = br(rmin["reducao2"]), rmin["id"]
    m["reducaoDoisMax"], m["reducaoDoisMaxId"] = br(rmax["reducao2"], 1), rmax["id"]
    m["nPioraDois"] = str(sum(1 for x in comp if x["reducao2"] < -1e-9))
    m["nReducaoUm"] = str(sum(1 for x in comp if x["reducao2"] >= 1))
    top = sorted(comp, key=lambda x: -x["reducao2"])[:5]
    m["maioresReducoesDois"] = ", ".join(x["id"] for x in top)
    m["maioresReducoesMmax"] = str(max(x["M"] for x in top))
    grandes = [x for x in comp if x["M"] >= 1000]
    m["nGrandes"] = str(len(grandes))
    m["nGrandesAbaixoUm"] = str(sum(1 for x in grandes if x["reducao2"] < 1))
    ruins = [por_inst[CITADAS[k]] for k in ("idExemplo", "idInstUm", "idInstDois", "idDoisUmUm")]
    m["reducaoRuimMin"] = br(min(x["reducao2"] for x in ruins), 1)
    m["reducaoRuimMax"] = br(max(x["reducao2"] for x in ruins), 1)
    m["gapLbUm"] = br(st.mean(x["gap_lb1"] for x in comp))
    m["gapLbDois"] = br(st.mean(x["gap_lb2"] for x in comp))
    m["fechadoDois"] = br(st.mean(x["fechado2"] for x in comp), 1)
    m["melhoriaDois"] = br(st.mean(f(x["r2"]["melhoria_media_pct"]) for x in todas))
    m["tempoMedioDois"] = br(st.mean(f(x["r2"]["t_total_medio"]) for x in todas), 2)
    lenta2 = max(todas, key=lambda x: f(x["r2"]["t_total_medio"]))
    m["tempoMaxDois"], m["tempoMaxDoisId"] = br(f(lenta2["r2"]["t_total_medio"]), 2), lenta2["id"]
    m["cvFinDoisMax"] = br(max(100 * f(x["r2"]["final_dp"]) / f(x["r2"]["final_media"]) for x in todas), 3)
    m["divididasDois"] = br(st.mean(100 * x["divididas"] / x["salas"] for x in todas), 1)
    m["partNSeis"] = br(participacao(todas, "N6_dividir", "execs2"), 1)
    inv2 = [x for x in todas if x.get("inviavel")]
    if inv2:
        x = inv2[0]
        m["finalInviavelDois"], m["gapLbInviavelDois"] = br(x["fin2"]), br(x["gap_lb2"], 1)
        m["divididasInviavelDois"] = str(x["divididas"])
    ex2 = por_inst[CITADAS["idExemplo"]]
    m["finalExemploDois"], m["reducaoExemploDois"] = br(ex2["fin2"]), br(ex2["reducao2"], 1)
    m["divididasExemploDois"] = str(ex2["divididas"])
    m["gapLbExemplo"], m["gapLbExemploDois"] = br(ex2["gap_lb1"], 1), br(ex2["gap_lb2"], 1)
    linhas = ["% gerado por relatorio/gerar_figuras.py -- não editar"]
    linhas += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in m.items()]
    escrever("metricas.tex", linhas)
    return m


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    for antiga in FIG.glob("*.pdf"):        # versões antigas das figuras em PDF
        antiga.unlink()
    inst, inviaveis = carregar()
    todas = [x for x in inst + inviaveis if x.get("r2")]
    lin = sensibilidade(inst)
    fig_gaps(inst)
    fig_vizinhancas(inst, todas)
    fig_tempo(inst)
    fig_variabilidade(inst)
    fig_modelos(inst)
    fig_distribuicao(CITADAS["idGrupo"])
    fig_tipos_por_sala(todas)
    tab_instancias(inst, inviaveis)
    tab_resultados(inst)
    tab_resultados(todas, "r2", "resultados_tipos2.tex")
    tab_qualidade(inst)
    tab_vizinhancas(inst, todas)
    tab_tipos_por_sala(todas)
    tab_sensibilidade(lin)
    tab_distribuicao(CITADAS["idGrupo"])
    m = metricas(inst, inviaveis, lin)
    for k, v in m.items():
        print(f"{k:18s} {v}")
    print(f"k testados: {[l['k'] for l in lin]}")


if __name__ == "__main__":
    main()
