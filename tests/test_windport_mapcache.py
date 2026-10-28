"""Map-file cache (windport/mapcache.py). 3 processes call get_net repeatedly for 2 archetypes: the cache directory holds one file
per distinct map, the SHA-256 of each file equals that of archetypes.dumps, and no temporary files remain."""
import hashlib
import multiprocessing as mp
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from windport import archetypes as A                # noqa: E402

GEOS = [dict(kind="A1", n_cradles=4, cradle_mode="on_road"), dict(kind="A2", n_cradles=4, cradle_mode="on_road")]


def _work(d, rounds=6):
    sys.path.insert(0, str(ROOT))
    os.environ["WINDPORT_MAP_CACHE"] = d
    from windport import sim as S
    p = S.params(dict(horizon_h=10))
    out = []
    for _ in range(rounds):
        for g in GEOS:
            S._NETS.clear()                      # go through the disk cache every time
            D, net = S.get_net(g, p)
            out.append((net.map_sha256, hashlib.sha256(A.dumps(D)).hexdigest()))
    return out


def test_parallel_get_net_one_file_per_map():
    with tempfile.TemporaryDirectory() as d:     # pytest's tmp_path may not be writable
        with mp.get_context("spawn").Pool(3) as pool:
            res = [x for r in pool.map(_work, [d] * 3) for x in r]
        files = sorted(Path(d).iterdir())
        want = {hashlib.sha256(A.dumps(A.build(g["kind"], **{k: v for k, v in g.items() if k != "kind"}))).hexdigest() for g in GEOS}
        assert len(want) == 2 and {a for a, _ in res} == want and all(a == b for a, b in res)
        assert [f.name for f in files] == sorted(f"{s}.json" for s in want)
        assert all(hashlib.sha256(f.read_bytes()).hexdigest() == f.stem for f in files)


def test_corrupt_file_is_rewritten():
    from windport.mapcache import map_file
    with tempfile.TemporaryDirectory() as d:
        os.environ["WINDPORT_MAP_CACHE"] = d
        try:
            raw = b'{"x": 1}'
            f, sha = map_file(raw)
            f.write_bytes(b"broken")
            assert map_file(raw) == (f, sha) and f.read_bytes() == raw and len(os.listdir(d)) == 1
        finally:
            del os.environ["WINDPORT_MAP_CACHE"]
