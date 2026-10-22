"""Batch helpers shared by the experiment scripts: atomic JSON writes, pinning worker processes to cores, a small progress
file and a process pool that can share the machine with other jobs through a directory of CPU slots."""
import json
import os
import sys
import threading
import time


def write_json(path, obj, tries=40):
    """Write to a temporary file, then rename. On Windows the rename is refused while another process has the target open;
    wait a little and retry."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    for i in range(tries):
        try:
            return os.replace(tmp, path)
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(0.05)


def pin(cores):
    try:
        import psutil
        psutil.Process().cpu_affinity(cores)
    except Exception:     # without psutil (or where affinity is not supported) the processes are not pinned
        pass


class Progress:
    """Progress of a run in a small JSON file (path): counts of points, processes, state, the last lines."""

    def __init__(self, path, total, reused, procs, title, task="run"):
        self.path, self.lock = path, threading.Lock()
        self.d = dict(task=task, title=title, total=total, done=reused, reused=reused, failed=0, processes=procs,
                      started=time.time(), updated=time.time(), state="running", note="", recent=[])
        self.write()

    def write(self, **kw):
        with self.lock:
            self.d.update(kw, updated=time.time())
            try:
                write_json(self.path, self.d)
            except PermissionError:      # progress is for display only: if it cannot be written, try again next time
                pass

    def log(self, line, **kw):
        with self.lock:
            self.d["recent"] = (self.d["recent"] + [line])[-8:]
        self.write(**kw)

    def heartbeat(self, stop, every=30.0):
        while not stop.wait(every):
            self.write()


def slot_imap(func, items, procs, initializer=None, initargs=(), slots_dir=None, tag="run", ordered=False):
    """Replacement of mp.Pool(procs, initializer, initargs).imap_unordered(func, items): with machine-wide CPU slots
    (slots_dir, or the environment variable CPU_SLOTS: a directory with a module cpu_slots providing Slots) one slot is taken
    per item and given back when it is done; without them at most procs items are under way. Returns a generator of the
    results of func in the order of completion (ordered: a list in the order of items, once all are done, in place of
    pool.map). To stop early the caller closes the generator: no new items are started, the items under way are finished and
    the slots given back."""
    from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait

    def gen(index):
        slots, sd = None, slots_dir or os.environ.get("CPU_SLOTS")
        if sd:
            sys.path.insert(0, sd)
            from cpu_slots import Slots
            slots = Slots(f"{tag}-{os.getpid()}")
        todo, live = list(enumerate(items)), {}
        try:
            with ProcessPoolExecutor(procs, initializer=initializer, initargs=initargs) as ex:
                while todo or live:
                    if slots:
                        slots.want(len(todo) + len(live))
                    while todo and len(live) < procs and (slots is None or slots.take()):
                        i, x = todo.pop(0)
                        live[ex.submit(func, x)] = i
                    if not live:
                        time.sleep(0.5)            # no slot free: try again shortly
                        continue
                    done, _ = wait(live, timeout=0.5, return_when=FIRST_COMPLETED)
                    for f in done:
                        i = live.pop(f)
                        if slots:
                            slots.give()
                        yield (i, f.result()) if index else f.result()
        finally:
            if slots:
                slots.close()
    if ordered:
        return [r for _, r in sorted(gen(True), key=lambda x: x[0])]
    return gen(False)
