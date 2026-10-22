"""Exhaustive search for a small instance of a serial cut (Corollary 3): a single lane made of two exclusive blocks in series
with no passing place between them (discrete time, all states enumerated, no pruning, written like windport.exact).

Vehicle states: yard empty Y -> (pick-up hp) -> YL -> (up block 1, a1) -> U1 (at the block boundary, may stop there)
  -> (up block 2, a2: for the first o units the tail still covers block 1)
  -> QT (on the quay side, tail still covering block 2 for o units: in the occupancy model a loaded vehicle leaving the top of
  the chain still occupies the threshold g with its tail, see bound2._guard) -> quay side loaded QL -> (set-down hd, takes a
  cradle; direct lift S = 0: a vehicle in QL waits for the crane and is released when the lift starts) -> QE -> (down block 2,
  e2) -> E2 (at the block boundary, may stop)
  -> (down block 1, e1: for the first o units the tail still covers block 2) -> Y.
Each block holds at most one vehicle at a time (loaded and empty vehicles are both exclusive); the quay side (QT, QL, setting
down, QE) holds at most Qs vehicles; cradles: full + being set down <= S.
The crane lifts one by one within the window [G, G + L] (each lift entirely inside); cradle mode lifts from a full cradle,
direct lift from a vehicle in QL. At each time step settle first, then decide jointly, and check capacity with the counts after
the decisions (release before acquire, as in windport.exact). Empty-system start (at time 0 all vehicles in Y, cradles empty).
max_delivery returns the maximum number of pieces lifted on board in the window; chain_params gives (F, R, h), dq and start0
used by Corollary 3 (with the occupancy definitions of this model)."""
import itertools

Y, P_, YL, U1, U2, QL, D_, QE, E2, E1, QT = range(11)
QUAY = (QT, QL, D_, QE)


def _blocks(vs, c):
    """Number of vehicles on each block."""
    b1 = b2 = 0
    o = c["o"]
    for ph, rem in vs:
        if ph == U1 or ph == E1:
            b1 += 1
        if ph == U2 or ph == E2 or ph == QT:
            b2 += 1
        if ph == U2 and rem > c["a2"] - o:
            b1 += 1
        if ph == E1 and rem > c["e1"] - o:
            b2 += 1
    return b1, b2


def _ok(vs, F, c):
    b1, b2 = _blocks(vs, c)
    return b1 <= 1 and b2 <= 1 and sum(ph in QUAY for ph, _ in vs) <= c["Qs"] and F + sum(ph == D_ for ph, _ in vs) <= c["S"]


def _choices(ph, rem, c):
    out = [(ph, rem)]
    if rem == 0:
        if ph == Y:
            out.append((P_, c["hp"]))
        elif ph == YL:
            out.append((U1, c["a1"]))
        elif ph == U1:
            out.append((U2, c["a2"]))
        elif ph == QL and c["S"]:
            out.append((D_, c["hd"]))
        elif ph == QE:
            out.append((E2, c["e2"]))
        elif ph == E2:
            out.append((E1, c["e1"]))
    return out


NEXT = {P_: YL, U2: QT, QT: QL, D_: QE, E1: Y}          # automatic transition on expiry; U1 and E2 stop at the block boundary


def _decide(state, t, c, windows):
    vs, F, crane = state
    opts = [(vs, F, 0)]
    if crane == 0 and any(a <= t and t + c["p"] <= b for a, b in windows):
        if c["S"] and F:
            opts.append((vs, F - 1, 1))
        if not c["S"] and (QL, 0) in vs:
            k = vs.index((QL, 0))
            opts.append((vs[:k] + ((QE, 0),) + vs[k + 1:], F, 1))
    for vs1, F1, lift in opts:
        for combo in itertools.product(*(_choices(ph, rem, c) for ph, rem in vs1)):
            if _ok(combo, F1, c):
                yield (combo, F1, c["p"] if lift else crane), lift


def _advance(state, o=1):
    vs, F, crane = state
    out = []
    for ph, rem in vs:
        if rem:
            rem -= 1
            if rem == 0:
                F += ph == D_
                ph, rem = NEXT.get(ph, ph), (o if ph == U2 else 0)
        out.append((ph, rem))
    return tuple(sorted(out)), F, max(0, crane - 1)


def max_delivery(K, S, Qs, hp, a1, a2, e1, e2, hd, p, G, L, o=1):
    c = dict(K=K, S=S, Qs=Qs, hp=hp, a1=a1, a2=a2, e1=e1, e2=e2, hd=hd if S else 0, p=p, o=o)
    assert all(int(x) == x and x >= 1 for x in (hp, a1, a2, e1, e2, p, o)) and o < min(a2, e1) + 1 and (not S or hd >= 1)
    windows = [(G, G + L)]
    frontier = {((tuple((Y, 0) for _ in range(K))), 0, 0): 0}
    best = 0
    for t in range(G + L + 1):
        nxt = {}
        for s, v in frontier.items():
            for s2, lift in _decide(s, t, c, windows):
                v2 = v + lift
                best = max(best, v2)
                if t < G + L:
                    a = _advance(s2, o)
                    if nxt.get(a, -1) < v2:
                        nxt[a] = v2
        frontier = nxt
    return best


def chain_params(a1, a2, e1, e2, hd, S, o=1):
    """Parameters of Corollary 3 in this model (format of windport.bound2.chain_times): up-block order [1, 2], down [2, 1]."""
    up = ([0, a1], [a1 + a2 + o, a2 + o], [a1 + o, a2 + o])
    down = ([0, e2], [e2 + e1, e1], [e2 + o, e1])
    return dict(res=["b1", "b2"], up=up, down=down, dq=hd if S else 0, start0=0, top="b2", exit_first=True)
