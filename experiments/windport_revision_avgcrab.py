"""Near-yard buffer sensitivity: the extra crabbing time of each pick-up in the near-yard window uses the mean crabbing distance
of the slots (the main batch windport_revision --group c uses the farthest slot, which is conservative).
Okpo (one column of 9 slots; serial picking from a single column is the most sensitive) and Yantai only; turning level hi, switch
300 s, G = 24 h, K = 1-8, both cradle modes; otherwise as windport_revision.bnear_cfg.
Output: results/windport_revision_avgcrab_<config hash>/points.csv.
Run: python experiments/windport_revision_avgcrab.py --procs 8 --slots DIR
"""
import argparse
import hashlib
import itertools
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap, write_json      # noqa: E402
import windport_runs as T                                        # noqa: E402
import windport_revision as KK                                      # noqa: E402


def mean_extra(plan, v_l, v_e, tsw):
    cr = [x for c in plan["columns"] for x in c["crabs"]]
    m = sum(cr) / len(cr)
    return m / v_l + m / v_e + 4 * tsw


def keys():
    return [T.enc(dict(site=s, scen=sc, mode=m, K=K, lv="hi", G=24)) for s, sc, m, K in itertools.product(["okpo", "yantai"], ["base", "slow"], T.MODES, range(1, 9))]


def cfg(d, plans):
    import windport_revision_buffer as B
    from windport import sim as WS
    c = KK.bnear_cfg(d, plans)
    p0 = dict(WS.BASE, **T.SCEN[d["scen"]].get("p", {}))
    c["p"] = dict(c["p"], hp_s=p0["hp_s"] + mean_extra(plans[d["site"]], p0["v_loaded"], p0["v_empty"], KK.LEVELS["hi"][1]))
    assert B.crab_extra(plans[d["site"]], p0["v_loaded"], p0["v_empty"], 300.0) >= c["p"]["hp_s"] - p0["hp_s"]
    return c


_OUT, _PL = None, {}


def init(out, plans):
    global _OUT
    KK.init("c", {}, plans)
    _PL.update(plans)
    _OUT = Path(out)


def chunk(ks):
    import windport_design as X
    for k in ks:
        f = _OUT / "points" / T.fname(k)
        if not f.exists():
            write_json(f, dict(X.port_point(cfg(T.dec(k), _PL)), **T.dec(k), key=k))
    return ks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    import windport_design as X
    import windport_revision_lib as K
    X.setup_env()
    plans, pf = KK.load_plans(make=False)
    K.install_all(plans)
    _, tf = KK.turn_alt()
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in KK.code_files() + ["experiments/windport_revision_avgcrab.py"]}
    cf = dict(task="revision", part="avgcrab", code=code, plans_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(), turn_alt_sha256=hashlib.sha256(tf.read_bytes()).hexdigest())
    out = ROOT / "results" / f"windport_revision_avgcrab_{hashlib.sha256(json.dumps(cf, sort_keys=True).encode()).hexdigest()[:12]}"
    X.prepare(out, cf)
    ks = keys()
    todo = [k for k in ks if not (out / "points" / T.fname(k)).exists()]
    prog = Progress(out / "progress.json", len(ks), len(ks) - len(todo), a.procs, "near-yard pick-up with mean crabbing distance", "revision")
    for ds in slot_imap(chunk, [[k] for k in todo], a.procs, initializer=init, initargs=(str(out), plans), slots_dir=a.slots, tag="revision"):
        prog.write(done=prog.d["done"] + len(ds))
    rs = [json.loads((out / "points" / T.fname(k)).read_text(encoding="utf-8")) for k in ks]
    X.wcsv(out / "points.csv", [X.sim_row("codesign", k, r) for k, r in zip(ks, rs)])
    lb = sum(1 for r in rs if r["port_h"] is not None and r["port_h"] < r["lstar_lo"] - 1e-9)
    note = f"{len(rs)} points; checker failures {sum(1 for r in rs if not r['check_ok'])}; port time < L″_lift* {lb}; W″_lift(T_j) < j {sum(int(r.get('viol') or 0) for r in rs)} piles"
    prog.write(state="done", note=note)
    print(out.name, note)


if __name__ == "__main__":
    main()
