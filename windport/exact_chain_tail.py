"""Two-block chain enumeration, variant "lift from the vehicle while its tail still occupies the chain top block"
(small-case check of Corollary 6 extended to dq < 0; windport/exact_chain.py is unchanged, states, block counts and
choices are the same as there).

Only two differences from exact_chain:
  · with direct lifting (S = 0) and mixed lifting (mixed, S ≥ 1) the crane can also lift from a vehicle in QT (on the quay
    side, tail still on block 2); after the lift the vehicle enters QX (empty, tail still on block 2) and only after the
    tail leaves does it turn to QE and go down, so the two legs of the same vehicle do not overlap on a block. exact_chain
    lifts only from QL (tail clear), i.e. "lift only after the tail has left the single lane";
  · mixed: in cradle mode the crane can also lift from a vehicle in QL / QT (as in Corollary 2).
From an empty system; max_delivery returns the maximum number of piles lifted aboard within the window [G, G + L]."""
import itertools

from windport import exact_chain as X

Y, P_, YL, U1, U2, QL, D_, QE, E2, E1, QT = range(11)
QX = 11
QUAY = (QT, QL, D_, QE, QX)
NEXT = {**X.NEXT, QX: QE}


def _ok(vs, F, c):
    b1, b2 = X._blocks([(QT if ph == QX else ph, rem) for ph, rem in vs], c)        # QX occupies block 2 like QT
    return b1 <= 1 and b2 <= 1 and sum(ph in QUAY for ph, _ in vs) <= c["Qs"] and F + sum(ph == D_ for ph, _ in vs) <= c["S"]


def _decide(state, t, c, windows):
    vs, F, crane = state
    opts = [(vs, F, 0)]
    if crane == 0 and any(a <= t and t + c["p"] <= b for a, b in windows):
        if c["S"] and F:
            opts.append((vs, F - 1, 1))
        if not c["S"] or c["mixed"]:
            for k, (ph, rem) in enumerate(vs):
                if (ph, rem) == (QL, 0) or ph == QT:
                    new = (QE, 0) if ph == QL else (QX, rem)
                    opts.append((vs[:k] + (new,) + vs[k + 1:], F, 1))
    for vs1, F1, lift in opts:
        for combo in itertools.product(*(X._choices(ph, rem, c) for ph, rem in vs1)):
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


def max_delivery(K, S, Qs, hp, a1, a2, e1, e2, hd, p, G, L, o=1, mixed=False):
    c = dict(K=K, S=S, Qs=Qs, hp=hp, a1=a1, a2=a2, e1=e1, e2=e2, hd=hd if S else 0, p=p, o=o, mixed=mixed and S > 0)
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


if __name__ == "__main__":
    # self-check: with tail o = 1 and lifting only from QL (mixed = False, S ≥ 1: same state space as the cradle mode of
    # exact_chain) the result equals exact_chain
    for args in [(2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 12), (2, 0, 1, 1, 3, 1, 1, 1, 1, 1, 4, 9)]:
        if args[1]:
            assert max_delivery(*args) == X.max_delivery(*args), args
    assert max_delivery(2, 0, 1, 1, 1, 2, 2, 2, 1, 1, 0, 12, o=2) >= X.max_delivery(2, 0, 1, 1, 1, 2, 2, 2, 1, 1, 0, 12, 2)
    print("ok")
