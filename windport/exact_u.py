"""Exhaustive search for small instances of unloading (Theorem 3 of W1) and of unloading and loading sharing one cut (Theorem 4):
discrete time, all states enumerated, no pruning (written like windport.exact).

Model (integer time units; the cut is the only passage between the two sides, a single lane):
  load     yard empty Y -> (pick-up hp) -> YL -> (loaded crossing tl_o) -> quay side loaded QL -> (set-down hd, takes a
           cradle) -> quay side empty QE; the crane lifts from a cradle within the crane windows (with S = 0 from a vehicle in
           QL, released when the lift starts).
  unload   QE -> (ramp operation rho: the ramp is exclusive, the whole operation inside a ramp window) -> quay side loaded QU ->
           (loaded crossing tl_u) -> (set down on saddles hy) -> Y;
           QU may also put the monopile on a stand behind the ramp (hs, S_u stands), and a QE vehicle picks it up there (hs).
  empty    QE -> (to the yard te_y) -> Y; Y -> (to the quay te_q) -> QE.
  At most one loaded vehicle on the cut, and then no other vehicle; with no loaded vehicle at most qe empty vehicles. Quay zone
  (crossing towards the quay and every quay-side state): at most Q vehicles.
  At each time step: first settle the activities that end (set-down, put on a stand, ramp operation), then decide jointly, and
  check capacity with the counts after the decisions (release before acquire, as in windport.exact).
Counts: N_o = lifts started (and finished) in the crane windows, N_u = ramp operations finished in the ramp windows. The value is
the Pareto set of (N_o, N_u).
load / unload: switch off one flow (unload only is the model of Theorem 3; load only with the return across the cut is the same
model as windport.exact, which the tests compare case by case).
"""
import itertools

Y, P_, YL, CO, QL, D_, QE, CQ, CY, RU, QU, CU, YD, SD, SP = range(15)
NEXT = {P_: YL, CO: QL, D_: QE, CQ: QE, CY: Y, RU: QU, CU: YD, YD: Y, SD: QE, SP: QU}
ZONE = {CO, CQ, QL, D_, QE, RU, QU, SD, SP}
LCUT, ECUT = {CO, CU}, {CQ, CY}


def _ok(vs, F, Fu, c):
    nl = sum(ph in LCUT for ph, _ in vs)
    ne = sum(ph in ECUT for ph, _ in vs)
    return (nl <= 1 and (nl == 0 or ne == 0) and ne <= c["qe"] and sum(ph in ZONE for ph, _ in vs) <= c["Q"]
            and F + sum(ph == D_ for ph, _ in vs) <= c["S"] and Fu + sum(ph == SD for ph, _ in vs) <= c["Su"]
            and sum(ph == RU for ph, _ in vs) <= 1)


def _open(t, d, wins):
    return any(a <= t and t + d <= b for a, b in wins)


def _choices(ph, rem, c, t):
    """(next state, remaining time, whether a pile is taken from a stand); the first entry is to stay."""
    out = [(ph, rem, 0)]
    if rem:
        return out
    if ph == Y:
        if c["load"]:
            out.append((P_, c["hp"], 0))
        if c["unload"]:
            out.append((CQ, c["te_q"], 0))
    elif ph == YL:
        out.append((CO, c["tl_o"], 0))
    elif ph == QL and c["S"]:
        out.append((D_, c["hd"], 0))
    elif ph == QE:
        out.append((CY, c["te_y"], 0))
        if c["unload"] and _open(t, c["rho"], c["ramp"]):
            out.append((RU, c["rho"], 0))
        if c["Su"]:
            out.append((SP, c["hs"], 1))
    elif ph == QU:
        out.append((CU, c["tl_u"], 0))
        if c["Su"]:
            out.append((SD, c["hs"], 0))
    return out


def _decide(state, t, c):
    vs, F, Fu, crane = state
    opts = [(vs, F, 0)]
    if crane == 0 and _open(t, c["p"], c["crane"]):
        if c["S"] and F:
            opts.append((vs, F - 1, 1))
        if not c["S"] and (QL, 0) in vs:
            k = vs.index((QL, 0))
            opts.append((vs[:k] + ((QE, 0),) + vs[k + 1:], F, 1))
    for vs1, F1, lift in opts:
        for combo in itertools.product(*(_choices(ph, rem, c, t) for ph, rem in vs1)):
            take = sum(x[2] for x in combo)
            if take > Fu:
                continue
            nv = tuple((ph, rem) for ph, rem, _ in combo)
            if _ok(nv, F1, Fu - take, c):
                yield (nv, F1, Fu - take, c["p"] if lift else crane), lift


def _advance(state):
    vs, F, Fu, crane = state
    out, nu = [], 0
    for ph, rem in vs:
        if rem:
            rem -= 1
            if rem == 0:
                F += ph == D_
                Fu += ph == SD
                nu += ph == RU
                ph = NEXT[ph]
        out.append((ph, rem))
    return (tuple(sorted(out)), F, Fu, max(0, crane - 1)), nu


def _prune(xs):
    """Pareto set of (N_o, N_u) (larger is better for both)."""
    xs = sorted(set(xs), reverse=True)
    out, best_u = [], -1
    for o, u in xs:
        if u > best_u:
            out.append((o, u))
            best_u = u
    return tuple(sorted(out))


def all_states(c):
    """All states compatible with the resource constraints (crane idle, no ramp operation in progress - the ramp window starts at
    0 and is closed before): window starts for any history."""
    dur = {P_: c["hp"], CO: c["tl_o"], D_: c["hd"], CQ: c["te_q"], CY: c["te_y"], CU: c["tl_u"], YD: c["hy"], SD: c["hs"], SP: c["hs"]}
    kinds = [(Y, 0), (YL, 0), (QL, 0), (QE, 0), (QU, 0)] + [(ph, r) for ph, d in dur.items() for r in range(1, int(d) + 1)]
    drop = set()
    if not c["load"]:
        drop |= {P_, YL, CO, QL, D_}
    if not c["unload"]:
        drop |= {CQ, QU, CU, YD, SD, SP}
    if not c["S"]:
        drop.add(D_)
    if not c["Su"]:
        drop |= {SD, SP}
    kinds = [k for k in kinds if k[0] not in drop]
    out = set()
    for vs in itertools.combinations_with_replacement(sorted(kinds), c["K"]):
        for F in range(c["S"] + 1):
            for Fu in range(c["Su"] + 1):
                if _ok(vs, F, Fu, c):
                    out.add((tuple(vs), F, Fu, 0))
    return out


def frontier(K, S, p, hp, hd, tl_o, te_y, crane, Su=0, hs=1, rho=1, tl_u=1, te_q=1, hy=1, ramp=(), Q=None, qe=1, load=True,
             unload=True, start="empty"):
    """Pareto set of (N_o, N_u) in the windows. crane, ramp: open periods [(a, b)] (integers). start: empty (all vehicles empty
    on the yard side, cradles and stands empty), quay (all vehicles empty on the quay side), any (every compatible state)."""
    c = dict(K=K, S=S, p=p, hp=hp, hd=hd if S else 0, tl_o=tl_o, te_y=te_y, Su=Su, hs=hs, rho=rho, tl_u=tl_u, te_q=te_q, hy=hy,
             crane=list(crane), ramp=list(ramp), Q=K if Q is None else min(Q, K), qe=qe, load=load, unload=unload)
    assert all(int(x) == x and x >= 1 for x in (p, hp, tl_o, te_y, rho, tl_u, te_q, hy, hs, qe)) and (not S or hd >= 1)
    if start == "any":
        init = all_states(c)
    else:
        init = {(tuple(((Y if start == "empty" else QE), 0) for _ in range(K)), 0, 0, 0)}
    H = max([b for _, b in c["crane"]] + [b for _, b in c["ramp"]] + [0])
    fr = {s: ((0, 0),) for s in init}
    for t in range(H + 1):
        nxt = {}
        for s, vals in fr.items():
            for s2, lift in _decide(s, t, c):
                a, nu = _advance(s2) if t < H else (s2, 0)
                new = tuple((o + lift, u + nu) for o, u in vals)
                old = nxt.get(a)
                nxt[a] = new if old is None else _prune(old + new)
        fr = nxt
    return _prune(x for v in fr.values() for x in v)
