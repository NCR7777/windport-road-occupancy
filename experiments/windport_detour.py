"""T_rate of the transfer network on the Okpo detour route (node_trace_016 banned, windport_revision.BAN); evaluates the bound only,
no simulation.

T_rate = n_v / min{K/c, 1/(τ_l + τ_e)} (manuscript Section 3.3, Corollary 1 on the transfer network, delivery point at the near
yard): the same function as the "cycle" rows of windport_revision_r1_rated.py (tr_cfg → bound_all.parts(lift=True)["P"], K = 2,
n_v = 10), only with ban added to the geo of the transfer configuration; the alternative-turn times are taken from
"okpo|transfer_ban" of bturn (same as ban = 1 in btr_cfg of windport_revision).
Grid: yard × speed level (v1 = 1 km/h = slow, v25 = 2.5 km/h = base, r5 / r10 rated) × turn level (hi main rule / feas) × route
(original route ban = 0 / detour ban = 1, Okpo only).
Checks: (1) the original route reproduces Trate_* of rated2.csv (identical to two decimals); (2) detour T_rate ≤ T_seq* (T_seq_lb)
≤ T_seq, with buffer.tseq from numbers.json of the windport_revision report (K = 2, slow / base × hi / feas).
Output results/windport_detour_<config hash>/: numbers.json, rows.csv, config.json (input and code fingerprints).
Run: python experiments/windport_detour.py
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

H, KMH = 3600.0, 1 / 3.6
K_FLEET, N_V = 2, 10
SCEN = dict(v1="slow", v25="base")                              # speed level → manuscript scenario (key of the committed tseq)
CODE = ["experiments/windport_detour.py", "experiments/windport_revision_r1_rated.py", "experiments/windport_revision_analytic.py", "experiments/windport_revision.py",
        "experiments/windport_revision_lib.py", "experiments/windport_design_lib.py", "experiments/windport_netcache.py",
        "windport/bound_all.py", "windport/bound.py", "windport/bound_dead.py", "windport/bound_lift.py", "windport/sim4.py", "windport/main2.py", "windport/shipyard.py"]


def tr_cfg_ban(site, K, p, lv, plans, ban):
    """windport_revision_r1_rated.tr_cfg with a ban switch; ban = 0 equals it field by field."""
    import windport_design_lib as L
    import windport_revision as KK
    import windport_revision_r1_rated as R
    c = L.transfer_cfg(site, K, N_V, dict(p))
    nc = len(plans[site]["columns"])
    c["geo"] = dict(c["geo"], n_cradles=nc)
    c["S"] = nc
    if ban:
        c["geo"] = dict(c["geo"], ban=KK.BAN[site])
    c, _ = KK.plan_cfg(c, site, plans[site], dict(p), lv, "set")
    return KK.with_alt(c, site, "transfer_ban" if ban else "transfer", R.alt_scen(p), lv)


def trate_h(c):
    """T_rate (h) and (c, τ_l, τ_e): min{K/c, 1/(τ_l+τ_e)} is an upper bound on monopiles delivered per second."""
    from windport import bound_all as BA
    P = BA.parts(c, lift=True)["P"]
    rate = min(c["K"] / P.c, 1.0 / (P.tl + P.te)) * H
    return N_V / rate, dict(c_s=P.c, tl_s=P.tl, te_s=P.te, bind="K/c" if c["K"] / P.c <= 1.0 / (P.tl + P.te) else "1/(tl+te)")


def compute(plans):
    import windport_revision_analytic as KA
    rows = []
    for site in ("okpo", "yantai"):
        for ban in ((0, 1) if site == "okpo" else (0,)):
            for lv in ("hi", "feas"):
                for sp, p in KA.SPEEDS.items():
                    pp = dict(v_loaded=p.get("v_loaded", 2.5 * KMH), v_empty=p.get("v_empty", 5.0 * KMH))
                    t, d = trate_h(tr_cfg_ban(site, K_FLEET, pp, lv, plans, ban))
                    rows.append(dict(site=site, ban=ban, level=lv, speed=sp, T_rate_h=t, **d))
    return rows


def checks(rows, tseq, rated2):
    """(reproduction rows, order rows): reproduction = original route vs rated2.csv to two decimals; order = detour
    T_rate ≤ T_seq* ≤ T_seq (Okpo, K = 2)."""
    rep, order = [], []
    old = {(r["site"], r["level"]): r for r in rated2 if r["mode"] == "cycle"}
    for r in rows:
        if r["ban"] == 0:
            ref = float(old[(r["site"], r["level"])][f"Trate_{r['speed']}"])
            rep.append(dict(site=r["site"], level=r["level"], speed=r["speed"], now=round(r["T_rate_h"], 2), committed=ref, same=round(r["T_rate_h"], 2) == ref))
        if r["site"] == "okpo" and r["speed"] in SCEN:
            for ban in (0, 1):
                if r["ban"] != ban:
                    continue
                t = tseq[f"okpo|{SCEN[r['speed']]}|{r['level']}|{ban}|{K_FLEET}"]
                order.append(dict(level=r["level"], speed=r["speed"], ban=ban, T_rate=round(r["T_rate_h"], 3), T_seq_lb=t["T_seq_lb"], T_seq=t["T_seq"],
                                  ok=r["T_rate_h"] <= t["T_seq_lb"] + 1e-6 and t["T_seq_lb"] <= t["T_seq"]))
    return rep, order


def init():
    """Main geometry, transfer network, turn-ban overlay, network cache key (as windport_revision_r1_rated.main); returns
    (plans, plans file)."""
    import windport_design as X
    import windport_revision as KK
    import windport_revision_lib as K
    import windport_netcache as NC
    X.setup_env()
    NC.install()
    plans, pf = KK.load_plans(make=False)
    K.install_all(plans)
    return plans, pf


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import windport_design as X
    import windport_revision as KK
    plans, pf = init()
    rated_f = sorted(ROOT.glob("results/windport_revision_r1_rated_*/rated2.csv"))
    assert len(rated_f) == 1, rated_f
    num_f = ROOT / "results/tables/revision/numbers.json"
    bt = KK.turn_alt()[1]
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    cfg = dict(task="detour", code={f: sha(ROOT / f) for f in CODE}, maps=X.maps(), plans_sha256=sha(pf), ban=KK.BAN, k=K_FLEET, n_v=N_V,
               inputs={str(f.relative_to(ROOT)).replace("\\", "/"): sha(f) for f in (rated_f[0], num_f, bt)})
    out = ROOT / "results" / f"windport_detour_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    rows = compute(plans)
    tseq = json.loads(num_f.read_text(encoding="utf-8"))["buffer"]["tseq"]
    rated2 = list(csv.DictReader(open(rated_f[0], encoding="utf-8")))
    rep, order = checks(rows, tseq, rated2)
    with open(out / "rows.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(dict(r, T_rate_h=round(r["T_rate_h"], 6)) for r in rows)
    (out / "numbers.json").write_text(json.dumps(dict(
        trate={f"{r['site']}|{r['speed']}|{r['level']}|{r['ban']}": dict(T_rate=round(r["T_rate_h"], 3), **{k: round(r[k], 2) if k != "bind" else r[k] for k in ("c_s", "tl_s", "te_s", "bind")}) for r in rows},
        reproduce=rep, order=order, all_same=all(x["same"] for x in rep), all_ordered=all(x["ok"] for x in order), k=K_FLEET, n_v=N_V), ensure_ascii=False, indent=1), encoding="utf-8")
    for x in rep + order:
        print(x)
    print(out)


if __name__ == "__main__":
    main()
