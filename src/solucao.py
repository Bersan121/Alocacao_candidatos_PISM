"""Representação da solução e função de avaliação.

Modelo: cada SALA oferece um único tipo de prova; uma escola pode receber vários tipos (um por
sala).

Representação
  tipo_sala[j][r] in {-1, 0..5}: tipo da sala r da escola j (-1 = sem tipo, não recebe ninguém;
                                 o construtivo dá tipo a todas as salas)
  aloc[i]       in {0..N-1}    : escola do candidato i
  Derivados (mantidos incrementalmente pela busca local):
  cap[j, t]   = soma das capacidades das salas da escola j com tipo t
  carga[j, t] = número de candidatos do tipo t alocados na escola j
  A distribuição dos candidatos de (j, t) entre as salas desse tipo é feita no fim
  (`distribuir_salas`): como as salas de mesmo tipo na mesma escola são intercambiáveis,
  basta carga[j, t] <= cap[j, t] para existir uma distribuição que respeita cada sala.

Função de avaliação
  f(s) = soma de D[i, aloc[i]]. Não há penalização: o construtivo só gera soluções viáveis e
  todos os movimentos da busca local preservam a viabilidade.
"""
import numpy as np

from instancia import NOMES_TIPOS, NUM_TIPOS as T


class Solucao:
    def __init__(self, inst, tipo_sala, aloc):
        self.inst = inst
        self.tipo_sala = [np.asarray(ts, dtype=int).copy() for ts in tipo_sala]
        self.aloc = np.asarray(aloc, dtype=int).copy()
        self.recalcular()

    def recalcular(self):
        inst = self.inst
        self.cap = np.zeros((inst.N, T), int)
        for j, e in enumerate(inst.escolas):
            for s, t in zip(e.salas, self.tipo_sala[j]):
                if t >= 0:
                    self.cap[j, t] += s
        self.carga = np.zeros((inst.N, T), int)
        np.add.at(self.carga, (self.aloc, inst.tipo_cand), 1)
        self.custo = float(inst.D[np.arange(inst.M), self.aloc].sum())

    def copia(self):
        return Solucao(self.inst, self.tipo_sala, self.aloc)

    # ------------------------------------------------------------------------- salas
    def distribuir_salas(self):
        """Distribui os candidatos de cada (escola, tipo) entre as salas desse tipo, maiores
        primeiro (usa o menor número de salas). Devolve (sala[i], ocupacao[j][r])."""
        inst = self.inst
        sala = np.full(inst.M, -1)
        ocup = [np.zeros(len(e.salas), int) for e in inst.escolas]
        ordem = np.lexsort((np.arange(inst.M), inst.tipo_cand, self.aloc))
        inicio = 0
        while inicio < inst.M:
            i0 = ordem[inicio]
            j, t = self.aloc[i0], inst.tipo_cand[i0]
            fim = inicio
            while fim < inst.M and self.aloc[ordem[fim]] == j and inst.tipo_cand[ordem[fim]] == t:
                fim += 1
            salas = sorted((r for r in range(len(inst.escolas[j].salas)) if self.tipo_sala[j][r] == t),
                           key=lambda r: -inst.escolas[j].salas[r])
            k = 0
            for i in ordem[inicio:fim]:
                while k < len(salas) and ocup[j][salas[k]] >= inst.escolas[j].salas[salas[k]]:
                    k += 1
                if k == len(salas):
                    break                      # sem vaga: verificar() acusa
                sala[i] = salas[k]
                ocup[j][salas[k]] += 1
            inicio = fim
        return sala, ocup

    def verificar(self):
        """Verificação independente de todas as restrições. Devolve a lista de violações."""
        inst = self.inst
        erros = []
        if self.aloc.shape != (inst.M,) or (self.aloc < 0).any() or (self.aloc >= inst.N).any():
            return ["há candidato sem escola válida"]
        for j, e in enumerate(inst.escolas):
            if len(self.tipo_sala[j]) != len(e.salas):
                erros.append(f"escola {e.id}: número de salas diferente da instância")
        ref = Solucao(inst, self.tipo_sala, self.aloc)
        for j, t in zip(*np.nonzero(ref.carga > ref.cap)):
            erros.append(f"escola {inst.escolas[j].id}, tipo {NOMES_TIPOS[t]}: {ref.carga[j, t]} "
                         f"candidatos para {ref.cap[j, t]} vagas")
        sala, _ = self.distribuir_salas()
        if not erros and (sala < 0).any():
            erros.append("candidato sem sala")
        if abs(ref.custo - self.custo) > 1e-6 * max(1.0, abs(ref.custo)):
            erros.append(f"custo acumulado {self.custo} difere do recalculado {ref.custo}")
        return erros

    # ------------------------------------------------------------------------- relatórios
    def escolas_usadas(self):
        return int((self.carga.sum(1) > 0).sum())

    def salas_usadas(self):
        _, ocup = self.distribuir_salas()
        return int(sum((o > 0).sum() for o in ocup))

    def distribuicao(self):
        """Linhas (escola, tipo, salas, capacidade, candidatos, ocupacao_pct, dist_media)."""
        inst = self.inst
        d = inst.D[np.arange(inst.M), self.aloc]
        linhas = []
        for j, e in enumerate(inst.escolas):
            for t in range(T):
                if self.cap[j, t] == 0 and self.carga[j, t] == 0:
                    continue
                sel = (self.aloc == j) & (inst.tipo_cand == t)
                linhas.append((e.id, NOMES_TIPOS[t], int((self.tipo_sala[j] == t).sum()), int(self.cap[j, t]),
                               int(self.carga[j, t]),
                               100 * self.carga[j, t] / self.cap[j, t] if self.cap[j, t] else 0.0,
                               float(d[sel].mean()) if sel.any() else 0.0))
        return linhas

    def escrever(self, caminho, cabecalho=()):
        """Arquivo da solução: salas (tipo e ocupação) e alocação de cada candidato."""
        inst = self.inst
        sala, ocup = self.distribuir_salas()
        with open(caminho, "w") as f:
            for linha in cabecalho:
                f.write(f"# {linha}\n")
            f.write(f"# custo: {self.custo:.4f}\n")
            f.write(f"# escolas usadas: {self.escolas_usadas()}/{inst.N}  "
                    f"salas usadas: {self.salas_usadas()}/{inst.num_salas}\n")
            f.write("# SALAS (escola, sala, capacidade, tipo, ocupacao)\n")
            for j, e in enumerate(inst.escolas):
                for r, s in enumerate(e.salas):
                    t = self.tipo_sala[j][r]
                    f.write(f"{e.id}, {r + 1}, {s}, {NOMES_TIPOS[t] if t >= 0 else '-'}, {ocup[j][r]}\n")
            f.write("# ALOCACAO (candidato, tipo, escola, sala, distancia)\n")
            for i, c in enumerate(inst.candidatos):
                j = self.aloc[i]
                f.write(f"{c.id}, {NOMES_TIPOS[c.tipo]}, {inst.escolas[j].id}, {sala[i] + 1}, "
                        f"{inst.D[i, j]:.4f}\n")
