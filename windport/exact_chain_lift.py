"""Two-block chain enumeration under the conservative lifting rule (windport/exact_chain.py and exact_chain_tail.py are unchanged;
states, block counts and choices are the same as theirs).

The crane lifts from a vehicle only in QL (vehicle on the quay side, tail clear of block 2): with direct lifting (S = 0)
this is the same as exact_chain; with mixed lifting (S ≥ 1) the crane can also lift from a full cradle, or from a vehicle
in QL (released on lifting, x = 0). exact_chain_tail allows lifting from QT (tail still on block 2) and is the comparison
for the original semantics.
No passage under the load (tu ≥ 0): for tu time units after each lift starts (from a vehicle or from a cradle), threshold
g (between the quay side and block 2) is closed: no vehicle can enter the quay side (an arriving vehicle waits at the end
of block 2) or leave it (QE cannot turn to E2); tu = 0 gives the base version.
In this model placement starts from QL (tail clear), so it cannot represent the case of the road-occupancy model where
placement completes before the tail leaves the single lane (covered by the random regression and the independent model).
From an empty system; max_delivery returns the maximum number of piles lifted aboard within the window [G, G + L]."""
import itertools

from windport import exact_chain as X

Y, P_, YL, U1, U2, QL, D_, QE, E2, E1, QT = range(11)


def _decide(state, t, c, windows):
    vs, F, crane, blk = state
    opts = [(vs, F, 0)]
    if crane == 0 and any(a <= t and t + c["p"] <= b for a, b in windows):
        if c["S"] and F:
            opts.append((vs, F - 1, 1))
        if not c["S"] or c["mixed"]:
            for k, (ph, rem) in enumerate(vs):
                if (ph, rem) == (QL, 0):
                    opts.append((vs[:k] + ((QE, 0),) + vs[k + 1:], F, 1))
    for vs1, F1, lift in opts:
        b = c["tu"] if lift and c["tu"] else blk
        for combo in itertools.product(*(_choices(ph, rem, c, b) for ph, rem in vs1)):
            if X._ok(combo, F1, c):
                yield (combo, F1, c["p"] if lift else crane, b), lift


def _choices(ph, rem, c, blk):
    out = X._choices(ph, rem, c)
    return [x for x in out if not (blk and ph == QE and x[0] == E2)]          # no departure while g is closed


def _advance(state, o=1):
    vs, F, crane, blk = state
    blk = max(0, blk - 1)
    out = []
    for ph, rem in vs:
        if rem:
            rem -= 1
            if rem == 0:
                F += ph == D_
                if ph != U2:
                    ph = X.NEXT.get(ph, ph)
        if ph == U2 and rem == 0 and not blk:                                 # arrival: wait at block 2 end while g closed
            ph, rem = QT, o
        out.append((ph, rem))
    return tuple(sorted(out)), F, max(0, crane - 1), blk


def max_delivery(K, S, Qs, hp, a1, a2, e1, e2, hd, p, G, L, o=1, mixed=False, tu=0):
    c = dict(K=K, S=S, Qs=Qs, hp=hp, a1=a1, a2=a2, e1=e1, e2=e2, hd=hd if S else 0, p=p, o=o, mixed=mixed and S > 0, tu=tu)
    assert all(int(x) == x and x >= 1 for x in (hp, a1, a2, e1, e2, p, o)) and o < min(a2, e1) + 1 and (not S or hd >= 1) and tu >= 0
    windows = [(G, G + L)]
    frontier = {((tuple((Y, 0) for _ in range(K))), 0, 0, 0): 0}
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
