"""Intermediate level of the fixed-duration representation: "the cut as a single resource" (windport/sim.py and sim2.py are
unchanged).

As the fixed-duration representation (fixed in windport.sim: roads and junctions are not checked for conflicts; ramp, stops,
holding places, cradles, crane and calendar as before; speeds unchanged, i.e. conflict-free travel times), and in addition every
single lane (the corridor sections recorded by the layout plus the junction resources between them; in A3 lane 2, i.e. loop, is a
separate one) is one resource of capacity 1: the windows of one leg on that lane are combined into a single [earliest entry,
latest release] window, and loaded and empty vehicles both hold it exclusively for the whole span (seize-delay-release). Loaded
vehicles hold it for t_ℓ, empty ones for t_e, taken as the union of the same windows as in the occupancy model.
Not included: road sections and junctions outside the single lanes, blocks along a chain (same-direction following), thresholds,
junction sweep.
The two one-way single lanes of A3 are separate resources.
simulate3(cfg) returns (net, p, sim, result), the result as in windport.sim.result; sim.cut is the resource set of each single
lane. Independent check: windport/check3.py."""
from windport import sim as WS
from windport import sim2 as S2


def cut_res(g):
    """The combined resource of single lane g."""
    return ("r", "__cut__", g)


def lanes(D, net):
    """Resources of each single lane (tuple, one frozenset per lane): road sections and the junction resources between them."""
    W = D["windport"]
    groups = [list(W.get("corridor") or [])] + ([list(W.get("loop") or [])] if W["kind"] == "A3" else [])
    out = []
    for roads in groups:
        if not roads:
            continue
        s = {("r", r) for r in roads}
        ends = [{D["roads"][r]["fromNodeId"], D["roads"][r]["toNodeId"]} for r in roads]
        for i, a in enumerate(ends):
            for b in ends[i + 1:]:
                s |= {("n", n) for n in a & b if n in net.node_res}
        out.append(frozenset(s))
    return tuple(out)


class CutSim(WS.PortSim):
    def __init__(self, *a, cut=(), **kw):
        super().__init__(*a, **kw)
        assert self.fixed, "the cut as a single resource is a level of the fixed-duration representation: fixed = True"
        self.cut = tuple(cut)
        for g in range(len(self.cut)):
            self.cap[cut_res(g)] = 1.0

    def kept(self, W):
        """Idempotent (PortSim.book filters the windows already filtered by trial once more): combined single-lane windows are
        kept as they are."""
        out = [w for w in W if w[0][0] in ("b", "c") or w[0] in self.ramp_res or w[0][1] == "__cut__"]
        for g, s in enumerate(self.cut):
            lane = [w for w in W if w[0] in s and len(w) > 1]
            if lane:
                out.append((cut_res(g), min(w[1] for w in lane), max(w[2] for w in lane), 1.0))
        return out


def simulate3(cfg):
    D, net, p, tasks, starts, quay, cal = S2.setup2(cfg)
    lift = "direct" if cfg["S"] == 0 else cfg.get("lift", "cradle")
    gate, yard = S2.idle_nodes(D)
    sim = CutSim(net, p, cfg["K"], tasks, starts, quay, cal, lift, True, WS.ramp_res(D), record=cfg.get("record", False),
                 exit=gate, yard=yard, hold=WS.hold_of(cfg), cut=lanes(D, net))
    sim.run()
    res = WS.result(cfg, D, net, p, sim, cal)
    res["idle"] = [gate, yard]
    return net, p, sim, res
