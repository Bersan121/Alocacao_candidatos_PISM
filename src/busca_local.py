"""Busca local: VND com 5 vizinhanças (um tipo de prova por sala).

Vizinhanças de alocação (as salas não mudam):
  N1 shift   : o candidato i vai para outra escola com vaga numa sala do seu tipo.
  N2 swap    : dois candidatos do mesmo tipo em escolas diferentes trocam de escola. Para cada par
               de escolas (j, k) a melhor troca sai em O(|I_j| + |I_k|):
               min_a (D[a,k] - D[a,j]) + min_b (D[b,j] - D[b,k]).
  N3 cadeias : cadeias de ejeção. Para cada tipo t, grafo cujos nós são as escolas com sala do
               tipo t e um nó extra S; arco j->k com custo min_{i em (j,t)} (D[i,k] - D[i,j]),
               arco S->j com custo 0 e j->S com custo 0 se j tem vaga do tipo t. Um ciclo negativo
               (Bellman-Ford) é uma sequência de realocações que melhora f. Sem ciclo negativo, a
               alocação é ótima para as salas atuais (otimalidade do problema de transporte).
Vizinhanças de salas:
  N4 retipar : a sala r da escola j muda do tipo u para o tipo t.
  N5 trocar  : duas salas da mesma escola, de tipos u != t e capacidades s1 > s2, trocam de tipo
               (u perde s1 - s2 vagas na escola, t ganha s1 - s2): ajuste fino da capacidade.
  Os dois são "transferir L vagas do tipo u para o tipo t na escola j". Avaliação do vizinho:
    chegadas = até L candidatos do tipo t de outras escolas com maior ganho D[i,atual] - D[i,j] > 0;
    despejos = se a carga de u passar da nova capacidade, sai o excedente, cada um para a escola
               com vaga do tipo u mais próxima (guloso, menor aumento de custo primeiro);
    delta    = custo dos despejos - ganho das chegadas. Aceita se delta < 0 (first improvement).
  Todo movimento preserva a viabilidade: chegadas só ocupam vagas novas, despejos só vão para
  escolas com vaga do seu tipo, e o movimento é descartado se não houver vagas para os despejos.

Estratégia (VND): N1 -> N2 -> N3 -> N4 -> N5. N1, N2 e N3 são aplicadas até o ótimo local da
vizinhança (todos os movimentos de melhora); N4 e N5 aplicam o primeiro movimento de melhora.
Sempre que uma vizinhança melhora a solução, volta para N1; termina quando nenhuma melhora.
"""
import heapq
import time

import numpy as np

from instancia import NOMES_TIPOS, NUM_TIPOS as T

EPS = 1e-9
NOMES = ("N1_shift", "N2_swap", "N3_cadeias", "N4_retipar", "N5_trocar")


class BuscaLocal:
    def __init__(self, sol, traco=None):
        self.s = sol
        self.inst = sol.inst
        self.D = self.inst.D
        self.tc = self.inst.tipo_cand
        self.ids_t = [np.flatnonzero(self.tc == t) for t in range(T)]
        self.traco = traco
        self.stats = {n: {"movs": 0, "ganho": 0.0, "tempo": 0.0} for n in NOMES}

    def _log(self, msg):
        if self.traco is not None:
            self.traco.write(msg + "\n")

    def _cid(self, i):
        return self.inst.candidatos[i].id

    def _eid(self, j):
        return self.inst.escolas[j].id

    def mover(self, i, k):
        s, t, j = self.s, self.tc[i], self.s.aloc[i]
        s.custo += self.D[i, k] - self.D[i, j]
        s.carga[j, t] -= 1
        s.carga[k, t] += 1
        s.aloc[i] = k

    # ------------------------------------------------------------------------- N1
    def n1_shift(self):
        s, D = self.s, self.D
        movs = 0
        while True:
            moveu = False
            for t in range(T):
                ids = self.ids_t[t]
                vag = s.cap[:, t] - s.carga[:, t]
                if len(ids) == 0 or not (vag > 0).any():
                    continue
                cur = D[ids, s.aloc[ids]]
                ganho = cur - np.where(vag > 0, D[ids], np.inf).min(1)
                cand = np.flatnonzero(ganho > EPS)
                for x in cand[np.argsort(-ganho[cand])]:
                    i = ids[x]
                    ok = np.flatnonzero(s.cap[:, t] > s.carga[:, t])
                    if len(ok) == 0:
                        break
                    k = ok[D[i, ok].argmin()]
                    if D[i, k] < D[i, s.aloc[i]] - EPS:
                        self._log(f"  N1 {self._cid(i)}: {self._eid(s.aloc[i])} -> {self._eid(k)} "
                                  f"delta={D[i, k] - D[i, s.aloc[i]]:.4f}")
                        self.mover(i, k)
                        movs += 1
                        moveu = True
            if not moveu:
                return movs

    # ------------------------------------------------------------------------- N2
    def n2_swap(self):
        s, D = self.s, self.D
        movs = 0
        while True:
            antes = movs
            for t in range(T):
                ids = self.ids_t[t]
                escolas = np.flatnonzero(s.cap[:, t] > 0)
                for a_, j in enumerate(escolas):
                    for k in escolas[a_ + 1:]:
                        while True:
                            al = s.aloc[ids]
                            Ij, Ik = ids[al == j], ids[al == k]
                            if len(Ij) == 0 or len(Ik) == 0:
                                break
                            da = D[Ij, k] - D[Ij, j]
                            db = D[Ik, j] - D[Ik, k]
                            ia, ib = da.argmin(), db.argmin()
                            if da[ia] + db[ib] >= -EPS:
                                break
                            self._log(f"  N2 {self._cid(Ij[ia])} ({self._eid(j)}) <-> {self._cid(Ik[ib])} "
                                      f"({self._eid(k)}) delta={da[ia] + db[ib]:.4f}")
                            self.mover(Ij[ia], k)
                            self.mover(Ik[ib], j)
                            movs += 1
            if movs == antes:
                return movs

    # ------------------------------------------------------------------------- N3
    def _ciclo_negativo(self, t):
        s, D, N = self.s, self.D, self.inst.N
        S = N
        ks = np.flatnonzero(s.cap[:, t] > 0)
        if len(ks) < 2:
            return None
        ids = self.ids_t[t]
        al = s.aloc[ids]
        W = np.full((N + 1, N + 1), np.inf)
        quem = np.full((N + 1, N + 1), -1)
        for j in ks:
            Ij = ids[al == j]
            if len(Ij) == 0:
                continue
            outros = ks[ks != j]
            delta = D[np.ix_(Ij, outros)] - D[Ij, j][:, None]
            am = delta.argmin(0)
            W[j, outros] = delta[am, np.arange(len(outros))]
            quem[j, outros] = Ij[am]
        W[S, ks] = 0
        vag = s.cap[:, t] - s.carga[:, t]
        W[ks[vag[ks] > 0], S] = 0
        # Bellman-Ford a partir de uma fonte virtual ligada a todos os nós (dist inicial 0)
        dist = np.zeros(N + 1)
        pred = np.full(N + 1, -1)
        x = -1
        for _ in range(N + 1):
            cand = dist[:, None] + W
            u = cand.argmin(0)
            nd = cand[u, np.arange(N + 1)]
            rel = nd < dist - EPS
            if not rel.any():
                return None
            dist[rel] = nd[rel]
            pred[rel] = u[rel]
            x = int(np.flatnonzero(rel)[0])
        for _ in range(N + 1):
            x = pred[x]
        ciclo, v = [], x
        while True:
            ciclo.append(v)
            v = pred[v]
            if v == x:
                break
        ciclo.reverse()                                   # arcos ciclo[a] -> ciclo[a+1]
        arcos = [(ciclo[a], ciclo[(a + 1) % len(ciclo)]) for a in range(len(ciclo))]
        if sum(W[u, w] for u, w in arcos) >= -EPS:
            return None
        return [(quem[u, w], w) for u, w in arcos if u != S and w != S]

    def n3_cadeias(self):
        movs = 0
        while True:
            antes = movs
            for t in range(T):
                while True:
                    cadeia = self._ciclo_negativo(t)
                    if not cadeia:
                        break
                    delta = sum(self.D[i, w] - self.D[i, self.s.aloc[i]] for i, w in cadeia)
                    self._log(f"  N3 {NOMES_TIPOS[t]}: " + ", ".join(
                        f"{self._cid(i)} {self._eid(self.s.aloc[i])}->{self._eid(w)}" for i, w in cadeia)
                        + f" delta={delta:.4f}")
                    for i, w in cadeia:
                        self.mover(i, w)
                    movs += 1
            if movs == antes:
                return movs

    # ------------------------------------------------------------------------- N4 / N5
    def _transferir(self, j, u, t, L):
        """Avalia transferir L vagas do tipo u para o tipo t na escola j.
        Devolve (delta, despejos[(i, destino)], chegadas[i]) ou None se não melhora/inviável."""
        s, D = self.s, self.D
        # chegadas: candidatos do tipo t de outras escolas que ganham indo para j
        ids = self.ids_t[t]
        fora = ids[s.aloc[ids] != j]
        g = D[fora, s.aloc[fora]] - D[fora, j]
        pos = np.flatnonzero(g > EPS)
        vagas = s.cap[j, t] + L - s.carga[j, t]
        if len(pos) == 0 or vagas <= 0:
            return None
        top = pos[np.argsort(-g[pos])[:vagas]]
        chegadas, ganho = fora[top], g[top].sum()
        # despejos: excedente do tipo u na escola j
        despejos, custo = [], 0.0
        exc = s.carga[j, u] - (s.cap[j, u] - L)
        if exc > 0:
            vag = s.cap[:, u] - s.carga[:, u]
            vag[j] = 0
            if vag.sum() < exc:
                return None
            Iu = self.ids_t[u][s.aloc[self.ids_t[u]] == j]

            def melhor(i):
                ok = np.flatnonzero(vag > 0)
                k = ok[D[i, ok].argmin()]
                return D[i, k] - D[i, j], k

            heap = []
            for i in Iu:
                c, k = melhor(i)
                heap.append((c, int(i), int(k)))
            heapq.heapify(heap)
            while len(despejos) < exc:
                c, i, k = heapq.heappop(heap)
                if vag[k] <= 0:                      # destino lotou: recalcula
                    c, k = melhor(i)
                    heapq.heappush(heap, (c, i, int(k)))
                    continue
                vag[k] -= 1
                custo += c
                despejos.append((i, k))
                if custo >= ganho - EPS:
                    return None
        delta = custo - ganho
        return (delta, despejos, chegadas) if delta < -EPS else None

    def _aplicar_transferencia(self, j, u, t, L, despejos, chegadas):
        s = self.s
        s.cap[j, u] -= L
        s.cap[j, t] += L
        for i, k in despejos:
            self.mover(i, k)
        for i in chegadas:
            self.mover(i, j)

    def _classes(self, j):
        """Salas da escola j agrupadas por (capacidade, tipo): salas iguais geram o mesmo vizinho."""
        cl = {}
        for r, (cap, u) in enumerate(zip(self.inst.escolas[j].salas, self.s.tipo_sala[j])):
            cl.setdefault((cap, int(u)), r)
        return cl

    def n4_retipar(self):
        for j in range(self.inst.N):
            for (cap, u), r in self._classes(j).items():
                for t in range(T):
                    if t == u:
                        continue
                    res = self._transferir(j, u, t, cap)
                    if res:
                        delta, desp, cheg = res
                        self._log(f"  N4 {self._eid(j)} sala {r + 1} ({cap}) "
                                  f"{NOMES_TIPOS[u]} -> {NOMES_TIPOS[t]}: "
                                  f"{len(cheg)} chegam, {len(desp)} saem, delta={delta:.4f}")
                        self.s.tipo_sala[j][r] = t
                        self._aplicar_transferencia(j, u, t, cap, desp, cheg)
                        return 1
        return 0

    def n5_trocar(self):
        for j in range(self.inst.N):
            cl = list(self._classes(j).items())
            for (s1, u), r1 in cl:
                for (s2, t), r2 in cl:
                    if u == t or s1 <= s2:
                        continue
                    res = self._transferir(j, u, t, s1 - s2)
                    if res:
                        delta, desp, cheg = res
                        self._log(f"  N5 {self._eid(j)} sala {r1 + 1} ({s1}, {NOMES_TIPOS[u]}) <-> sala "
                                  f"{r2 + 1} ({s2}, {NOMES_TIPOS[t]}): {len(cheg)} chegam, "
                                  f"{len(desp)} saem, delta={delta:.4f}")
                        self.s.tipo_sala[j][r1], self.s.tipo_sala[j][r2] = t, u
                        self._aplicar_transferencia(j, u, t, s1 - s2, desp, cheg)
                        return 1
        return 0

    # ------------------------------------------------------------------------- VND
    def vnd(self, limite_s=None):
        viz = [self.n1_shift, self.n2_swap, self.n3_cadeias, self.n4_retipar, self.n5_trocar]
        t0 = time.perf_counter()
        self._log(f"== VND (inicial {self.s.custo:.4f})")
        k = 0
        while k < len(viz):
            if limite_s is not None and time.perf_counter() - t0 > limite_s:
                self._log("limite de tempo atingido")
                break
            antes, ti = self.s.custo, time.perf_counter()
            m = viz[k]()
            st = self.stats[NOMES[k]]
            st["movs"] += m
            st["ganho"] += antes - self.s.custo
            st["tempo"] += time.perf_counter() - ti
            if antes - self.s.custo > EPS:
                self._log(f"{NOMES[k]}: {m} movimento(s), custo {antes:.4f} -> {self.s.custo:.4f}")
                k = 0
            else:
                k += 1
        self._log(f"ótimo local do VND: {self.s.custo:.4f}")
        return self.s
