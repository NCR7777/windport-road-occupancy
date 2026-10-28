"""Disk cache for archetype map files, shared by sim.get_net, sim2.get_net and sim4.get_net4.

Files are named by the SHA-256 of their content, so each map is stored once; an existing file whose hash matches is reused,
otherwise the map is written to a temporary file in the same directory and atomically renamed (parallel processes never read a
half-written file; a good existing file is not replaced, see the comments in map_file).
Location: environment variable WINDPORT_MAP_CACHE; if unset, .cache/windport_maps/ in the repository (excluded by .gitignore).
"""
import hashlib
import os
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cache_dir():
    return Path(os.environ.get("WINDPORT_MAP_CACHE") or ROOT / ".cache" / "windport_maps")


def map_file(raw):
    """Map JSON bytes (output of archetypes.dumps) -> (file path, sha256 hex digest)."""
    sha = hashlib.sha256(raw).hexdigest()
    d = cache_dir()
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{sha}.json"
    for i in range(50):
        try:
            ok = hashlib.sha256(f.read_bytes()).hexdigest() == sha
        except FileNotFoundError:
            ok = None
        except PermissionError:           # Windows: another process is renaming onto this file
            time.sleep(0.02 * (i + 1))
            continue
        if ok:
            return f, sha
        fd, tmp = tempfile.mkstemp(dir=d, prefix=f"{sha[:16]}.", suffix=".tmp")
        with os.fdopen(fd, "wb") as w:
            w.write(raw)
        try:
            # File missing: use rename, which on Windows fails if another process has just created the target, so it is not
            # replaced (replacing would break processes reading it); os.replace only when the content is wrong (corrupt)
            (os.rename if ok is None else os.replace)(tmp, f)
            return f, sha
        except (FileExistsError, PermissionError):     # created by another process (same content); reused next round
            os.unlink(tmp)
            time.sleep(0.02 * (i + 1))
    raise RuntimeError(f"cannot write map cache file {f}")
