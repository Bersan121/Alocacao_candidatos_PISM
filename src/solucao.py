"""Representação da solução e função de avaliação.

Modelo: cada SALA oferece até `max_tipos` tipos de prova (1 ou 2); uma escola pode receber
vários tipos. Com 2 tipos, a sala é dividida: parte das vagas fica com cada tipo.

Representação
  tipo_sala[j][r] in {-1, 0..5}: tipo principal da sala r da escola j (-1 = sem tipo, não recebe
                                 ninguém; o construtivo dá tipo a todas as salas)
  tipo2[j][r]     in {-1, 0..5}: segundo tipo da sala (-1 = nenhum; sempre -1 com max_tipos = 1)
  vagas2[j][r]                 : vagas da sala reservadas ao segundo tipo (0 se não há); o tipo
                                 principal fica com as demais
  aloc[i]       in {0..N-1}    : escola do candidato i
  As três listas de salas andam juntas como a tupla `st = (tipo_sala, tipo2, vagas2)`.
  Derivados (mantidos incrementalmente pela busca local):
  cap[j, t]   = vagas do tipo t na escola j (soma, sobre as salas, das vagas da sala dadas a t)
  carga[j, t] = número de candidatos do tipo t alocados na escola j
  A distribuição dos candidatos de (j, t) entre as salas desse tipo é feita no fim
  (`distribuir_salas`): como as vagas do mesmo tipo na mesma escola são intercambiáveis,
  basta carga[j, t] <= cap[j, t] para existir uma distribuição que respeita cada sala.

Função de avaliação
  f(s) = soma de D[i, aloc[i]]. Não há penalização: o construtivo só gera soluções viáveis e
  todos os movimentos da busca local preservam a viabilidade.
"""
import numpy as np

from instancia import NOMES_TIPOS, NUM_TIPOS as T


def salas_vazias(inst):
    """st = (tipo_sala, tipo2, vagas2) com todas as salas sem tipo."""
    return ([np.full(len(e.salas), -1, dtype=int) for e in inst.escolas],
            [np.full(len(e.salas), -1, dtype=int) for e in inst.escolas],
            [np.zeros(len(e.salas), dtype=int) for e in inst.escolas])


def assentos(inst, st, j, r):
    """Vagas da sala r da escola j por tipo: {tipo: vagas} (vazio se a sala não tem tipo)."""
    tipo_sala, tipo2, vagas2 = st
    a = {}
    if tipo_sala[j][r] >= 0:
        a[int(tipo_sala[j][r])] = int(inst.escolas[j].salas[r] - vagas2[j][r])
    if tipo2[j][r] >= 0:
        a[int(tipo2[j][r])] = int(vagas2[j][r])
    return a


def mover_assentos(inst, st, j, r, u, t, L):
    """Passa L vagas da sala r da escola j do tipo u para o tipo t (só as listas de salas; quem
    chama atualiza cap). O tipo principal só muda se perder todas as vagas."""
    tipo_sala, tipo2, vagas2 = st
    a = assentos(inst, st, j, r)
    a[u] -= L
    a[t] = a.get(t, 0) + L
    assert a[u] >= 0, "a sala não tem L vagas do tipo u"
    a = {x: n for x, n in a.items() if n > 0}
    assert len(a) <= 2
    p = next(x for x in (tipo_sala[j][r], tipo2[j][r], t) if x in a)
    outros = [x for x in a if x != p]
    tipo_sala[j][r] = p
    tipo2[j][r] = outros[0] if outros else -1
    vagas2[j][r] = a[outros[0]] if outros else 0


class Solucao:
    def __init__(self, inst, st, aloc, max_tipos=1):
        self.inst = inst
        self.max_tipos = max_tipos
        self.tipo_sala, self.tipo2, self.vagas2 = ([np.asarray(x, dtype=int).copy() for x in lista] for lista in st)
        self.aloc = np.asarray(aloc, dtype=int).copy()
        self.recalcular()

    @property
    def st(self):
        return self.tipo_sala, self.tipo2, self.vagas2

    def assentos(self, j, r):
        return assentos(self.inst, self.st, j, r)

    def mover_assentos(self, j, r, u, t, L):
        mover_assentos(self.inst, self.st, j, r, u, t, L)

    def recalcular(self):
        inst = self.inst
        self.cap = np.zeros((inst.N, T), int)
        for j, e in enumerate(inst.escolas):
            for r in range(len(e.salas)):
                for t, n in self.assentos(j, r).items():
                    self.cap[j, t] += n
        self.carga = np.zeros((inst.N, T), int)
        np.add.at(self.carga, (self.aloc, inst.tipo_cand), 1)
        self.custo = float(inst.D[np.arange(inst.M), self.aloc].sum())

    def copia(self):
        return Solucao(self.inst, self.st, self.aloc, self.max_tipos)

    # ------------------------------------------------------------------------- salas
    def distribuir_salas(self):
        """Distribui os candidatos de cada (escola, tipo) entre as salas desse tipo, as com mais
        vagas do tipo primeiro (usa o menor número de salas). Devolve (sala[i], ocupacao[j][r])."""
        inst = self.inst
        sala = np.full(inst.M, -1)
        ocup = [np.zeros(len(e.salas), int) for e in inst.escolas]
        ocup_t = {}                                    # (j, r, t) -> candidatos do tipo t na sala
        ordem = np.lexsort((np.arange(inst.M), inst.tipo_cand, self.aloc))
        inicio = 0
        while inicio < inst.M:
            i0 = ordem[inicio]
            j, t = self.aloc[i0], inst.tipo_cand[i0]
            fim = inicio
            while fim < inst.M and self.aloc[ordem[fim]] == j and inst.tipo_cand[ordem[fim]] == t:
                fim += 1
            vagas = {r: n for r in range(len(inst.escolas[j].salas))
                     for u, n in self.assentos(j, r).items() if u == t}
            salas = sorted(vagas, key=lambda r: -vagas[r])
            k = 0
            for i in ordem[inicio:fim]:
                while k < len(salas) and ocup_t.get((j, salas[k], t), 0) >= vagas[salas[k]]:
                    k += 1
                if k == len(salas):
                    break                      # sem vaga: verificar() acusa
                sala[i] = salas[k]
                ocup[j][salas[k]] += 1
                ocup_t[j, salas[k], t] = ocup_t.get((j, salas[k], t), 0) + 1
            inicio = fim
        return sala, ocup

    def verificar(self):
        """Verificação independente de todas as restrições. Devolve a lista de violações."""
        inst = self.inst
        erros = []
        if self.aloc.shape != (inst.M,) or (self.aloc < 0).any() or (self.aloc >= inst.N).any():
            return ["há candidato sem escola válida"]
        for j, e in enumerate(inst.escolas):
            if not len(self.tipo_sala[j]) == len(self.tipo2[j]) == len(self.vagas2[j]) == len(e.salas):
                erros.append(f"escola {e.id}: número de salas diferente da instância")
                continue
            for r, s in enumerate(e.salas):
                t1, t2, v2 = self.tipo_sala[j][r], self.tipo2[j][r], self.vagas2[j][r]
                if t2 < 0 and v2 != 0 or t2 >= 0 and not (t1 >= 0 and t2 != t1 and 0 < v2 < s):
                    erros.append(f"escola {e.id}, sala {r + 1}: divisão de vagas inválida "
                                 f"({t1}, {t2}, {v2} de {s})")
                if len(self.assentos(j, r)) > self.max_tipos:
                    erros.append(f"escola {e.id}, sala {r + 1}: mais de {self.max_tipos} tipo(s) de prova")
        ref = Solucao(inst, self.st, self.aloc, self.max_tipos)
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
                n_salas = sum(t in self.assentos(j, r) for r in range(len(e.salas)))
                linhas.append((e.id, NOMES_TIPOS[t], n_salas, int(self.cap[j, t]),
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
            if self.max_tipos > 1:
                f.write("# sala com 2 tipos: tipo = <tipo1>:<vagas>+<tipo2>:<vagas>\n")
            f.write("# SALAS (escola, sala, capacidade, tipo, ocupacao)\n")
            for j, e in enumerate(inst.escolas):
                for r, s in enumerate(e.salas):
                    a = self.assentos(j, r)
                    tipo = ("-" if not a else NOMES_TIPOS[next(iter(a))] if len(a) == 1
                            else "+".join(f"{NOMES_TIPOS[t]}:{n}" for t, n in a.items()))
                    f.write(f"{e.id}, {r + 1}, {s}, {tipo}, {ocup[j][r]}\n")
            f.write("# ALOCACAO (candidato, tipo, escola, sala, distancia)\n")
            for i, c in enumerate(inst.candidatos):
                j = self.aloc[i]
                f.write(f"{c.id}, {NOMES_TIPOS[c.tipo]}, {inst.escolas[j].id}, {sala[i] + 1}, "
                        f"{inst.D[i, j]:.4f}\n")
