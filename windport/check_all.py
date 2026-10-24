"""Independent check when the conservative lifting rule (windport/lift.py) is combined with the four spatial additions
(windport/sim4.py). Does not call Net.leg or the planning code of the simulation.

The checks of windport/check4.py (leg4 with alternative turns, crane reach as [s, s + p + t_sh], reserved periods) apply as
before; their base part windport.check.check is replaced by check of windport/check_lift.py (all checks of the original
checker + vehicle body clear of the road + area under the load), which also uses leg4 when rebuilding windows."""
from windport import check as C
from windport import check4 as C4
from windport import check_lift as CL


def check(net, p, trips, starts, quay, cal, fixed=False, ramp=(), hold=0, H=None, gate=None, yard=None, cut=False, reserve=None):
    """Arguments as windport/check4.check. Returns dict(ok, errors, max_ratio, n_far, n_res, n_clear, n_under)."""
    seen = {}

    def base(*a, **k):
        r = CL.check(*a, **k)
        seen.update(n_clear=r["n_clear"], n_under=r["n_under"])
        return r

    old = C.check
    C.check = base
    try:
        r = C4.check(net, p, trips, starts, quay, cal, fixed, ramp, hold, H, gate=gate, yard=yard, cut=cut, reserve=reserve)
    finally:
        C.check = old
    return dict(r, n_clear=seen.get("n_clear", 0), n_under=seen.get("n_under", 0))
