"""Maximum in-window delivery of a small instance: exhaustive search in discrete time (dynamic programming, all states enumerated,
no pruning). Used to check W1 (tests/test_windport_bound.py, experiments/windport_w1_check.py) and the exact column of Table 2.

Model (as windport.bound.lane, integer time units):
  vehicle: yard side empty Y -> (pick-up hp) -> yard side loaded YL -> (cross the cut tl) -> quay side loaded QL -> (set-down
      hd, takes one cradle) -> quay side empty QE -> (return: cross the cut te if te > 0; if te = 0 take the loop er, not using
      the cut) -> Y. Direct lift (S = 0): a vehicle in QL waits for the crane and becomes QE when the lift starts.
  cut: a loaded vehicle excludes every other vehicle from the cut; with no loaded vehicle at most qe empty vehicles are on it
      (qe = 1 means exclusive).
  quay zone (crossing towards the quay, QL, setting down, QE): at most Q vehicles. Cradles: full + being set down <= S.
  crane: lifts one by one within the windows [a, b]; a lift starting at t needs a <= t and t + p <= b. Cradle mode lifts from a
      full cradle (the cradle is freed when the lift starts), direct lift from a vehicle in QL; with mixed = True cradle mode can
      also lift from a vehicle in QL (the model of Corollary 2 of W1).
  At each time step: first settle the activities that end, then decide (crane first, then vehicles); all vehicle decisions are
  checked together against capacity using the counts *after* the decisions (release before acquire) - places freed by vehicles
  leaving the quay zone or the cut at this step can be used by vehicles entering at the same step. This matches the continuous
  time and half-open occupancy intervals of H1-H5.
Any decision may be postponed (waiting); states are symmetrised as multisets of vehicles, and each state keeps only the largest
number of pieces lifted on board.
"""
import itertools

Y, P_, YL, CL, QL, D_, QE, CE, R_ = range(9)
QUAY = (CL, QL, D_, QE)
NEXT = {P_: YL, CL: QL, D_: QE, CE: Y, R_: Y}


def _cut_ok(vs, qe):
    nl = sum(ph == CL for ph, _ in vs)
    ne = sum(ph == CE for ph, _ in vs)
    return nl <= 1 and (nl == 0 or ne == 0) and ne <= qe


def _ok(vs, F, cfg):
    return _cut_ok(vs, cfg["qe"]) and sum(ph in QUAY for ph, _ in vs) <= cfg["Q"] and F + sum(ph == D_ for ph, _ in vs) <= cfg["S"]


def _choices(ph, rem, cfg):
    """Next states a vehicle may choose at this time step (the first is to stay)."""
    out = [(ph, rem)]
    if rem == 0:
        if ph == Y:
            out.append((P_, cfg["hp"]))
        elif ph == YL:
            out.append((CL, cfg["tl"]))
        elif ph == QL and cfg["S"]:
            out.append((D_, cfg["hd"]))
        elif ph == QE:
            out.append((CE, cfg["te"]) if cfg["te"] > 0 else (R_, cfg["er"]))
    return out


def _decide(state, t, cfg, windows):
    """All decisions at time t: yields (state, number of lifts started at this step)."""
    vs, F, crane = state
    opts = [(vs, F, 0)]
    if crane == 0 and any(a <= t and t + cfg["p"] <= b for a, b in windows):
        if cfg["S"] and F:
            opts.append((vs, F - 1, 1))
        if (not cfg["S"] or cfg["mixed"]) and (QL, 0) in vs:
            k = vs.index((QL, 0))
            opts.append((vs[:k] + ((QE, 0),) + vs[k + 1:], F, 1))
    for vs1, F1, lift in opts:
        for combo in itertools.product(*(_choices(ph, rem, cfg) for ph, rem in vs1)):
            if _ok(combo, F1, cfg):
                yield (combo, F1, cfg["p"] if lift else crane), lift


def _advance(state):
    """Advance one time unit: settle activities that end (a finished set-down adds one full cradle)."""
    vs, F, crane = state
    out = []
    for ph, rem in vs:
        if rem:
            rem -= 1
            if rem == 0:
                F += ph == D_
                ph = NEXT[ph]
        out.append((ph, rem))
    return tuple(sorted(out)), F, max(0, crane - 1)


def all_states(cfg):
    """All states compatible with the resource constraints (crane idle): window starts for "any history"."""
    K, S = cfg["K"], cfg["S"]
    dur = {P_: cfg["hp"], CL: cfg["tl"], D_: cfg["hd"], CE: cfg["te"], R_: cfg["er"]}
    kinds = [(Y, 0), (YL, 0), (QL, 0), (QE, 0)] + [(ph, r) for ph, d in dur.items() for r in range(1, int(d) + 1)]
    if not S:
        kinds = [k for k in kinds if k[0] != D_]
    kinds = [k for k in kinds if k[0] != (CE if cfg["te"] == 0 else R_)]
    out = set()
    for vs in itertools.combinations_with_replacement(sorted(kinds), K):
        nd = sum(ph == D_ for ph, _ in vs)
        for F in range(0, S - nd + 1):
            if _ok(vs, F, cfg):
                out.add((tuple(vs), F, 0))
    return out


def max_delivery(L, p, S, K, hp, hd, tl, te, er=0, Q=None, G=0, T=None, n=1, start="empty", qe=1, mixed=False):
    """Maximum in-window delivery (pieces lifted on board). start = "empty": empty system at time 0 (all vehicles empty on the
    yard side, cradles empty), window i is [G + iT, G + iT + L] for i < n, returns the total over the n windows; start = "any":
    time 0 takes every compatible state (any history), only the window [0, L] is counted.
    qe: maximum number of empty vehicles on the cut when no loaded vehicle is on it; mixed: in cradle mode the crane may also lift
    from a vehicle."""
    cfg = dict(S=S, K=K, Q=K if Q is None else min(Q, K), p=p, hp=hp, hd=hd if S else 0, tl=tl, te=te, er=er, qe=qe,
               mixed=mixed and S > 0)
    assert all(int(x) == x and x >= 1 for x in (p, hp, tl, qe)) and (te >= 1 or er >= 1) and (not S or hd >= 1)
    if start == "any":
        windows, frontier = [(0, L)], {s: 0 for s in all_states(cfg)}
    else:
        T = T or 0
        windows = [(G + i * T, G + i * T + L) for i in range(n)]
        frontier = {((tuple((Y, 0) for _ in range(K))), 0, 0): 0}
    H = windows[-1][1]
    best = 0
    for t in range(H + 1):
        nxt = {}
        for s, v in frontier.items():
            for s2, lift in _decide(s, t, cfg, windows):
                v2 = v + lift
                best = max(best, v2)
                if t < H:
                    a = _advance(s2)
                    if nxt.get(a, -1) < v2:
                        nxt[a] = v2
        frontier = nxt
    return best
