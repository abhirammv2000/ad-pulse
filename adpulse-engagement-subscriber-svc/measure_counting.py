r"""
Time how fast the subscriber counts N billable renders from several threads.

MODE=new is for this code: record_event stores each event in this process, and
fold_forever runs in a separate process, as in production.
MODE=old only works on the first design, commit d852d51, where record_event counted each
event in its own transaction. It is how the "one transaction per event" numbers in
docs/DESIGN.md were measured.
SHAPE=one: every render is for the same ad. SHAPE=many: every render is for a different ad.
The time runs from the first event until the last one is counted in the reports. It also
checks that the report count and the ad's spend came out exact.

Run it in the subscriber image, against a MongoDB replica set and a Redis (it flushes that Redis):

    docker run --rm --network NET --entrypoint python \
      -e MODE=new -e SHAPE=one -e REDIS_HOST=redis \
      -e MONGODB_URI="mongodb://mongo:27017/?replicaSet=rs0" \
      -v "$PWD/measure_counting.py:/measure_counting.py:ro" SUBSCRIBER_IMAGE /measure_counting.py

N (default 2000) and THREADS (default 10) change the size. Run it a few times: on the first
design the rate swings from 11 to 165 events a second.
"""
import multiprocessing as mp
import os
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.environ.get("APP_DIR", "/app"))
import app  # noqa: E402
import redis  # noqa: E402
from pymongo import MongoClient, monitoring  # noqa: E402

URI = os.environ["MONGODB_URI"]
MODE = os.environ["MODE"]
SHAPE = os.environ["SHAPE"]
N = int(os.environ.get("N", "2000"))
THREADS = int(os.environ.get("THREADS", "10"))


class Attempts(monitoring.CommandListener):
    """Counts transaction attempts, since each attempt starts with a startTransaction command."""

    def __init__(self, counter=None):
        self.n = 0
        self.counter = counter
        self.lock = threading.Lock()

    def started(self, event):
        if event.command.get("startTransaction"):
            with self.lock:
                self.n += 1
                if self.counter is not None:
                    self.counter.value += 1

    def succeeded(self, event):
        pass

    def failed(self, event):
        pass


def fold_process(dbname, ready, stop, fold_attempts, fold_log):
    monitoring.register(Attempts(fold_attempts))
    client = MongoClient(URI)
    database = client[dbname]
    cache = redis.Redis(host=os.environ["REDIS_HOST"], decode_responses=True)
    original = app.fold

    def timed(*args, **kwargs):
        started = time.perf_counter()
        folded = original(*args, **kwargs)
        if folded:
            fold_log.append((folded, time.perf_counter() - started))
        return folded

    app.fold = timed
    ready.wait()
    app.fold_forever(client, database, cache, stop)


def main():
    dbname = f"contention_{MODE}_{SHAPE}_{int(time.time() * 1000)}"
    folder = None
    manager = mp.Manager()
    fold_log = manager.list()
    fold_attempts = mp.Value("i", 0)
    ready, stop = mp.Event(), mp.Event()
    if MODE == "new":
        folder = mp.Process(target=fold_process, args=(dbname, ready, stop, fold_attempts, fold_log))
        folder.start()

    attempts = Attempts()
    monitoring.register(attempts)
    client = MongoClient(URI)
    database = client[dbname]
    app.prepare_database(database)
    cache = redis.Redis(host=os.environ["REDIS_HOST"], decode_responses=True)
    cache.flushdb()

    now = datetime.now(timezone.utc)
    served = now - timedelta(seconds=1)

    def make(i):
        ad = "AD1" if SHAPE == "one" else f"AD{i}"
        campaign = "C1" if SHAPE == "one" else f"C{i}"
        return app.Engagement(ad, campaign, f"B{i}", served, "CPM", 1_000_000)

    events = [make(i) for i in range(N)]
    price = app.charge("render", events[0])
    results = []

    def record(chunk):
        for event in chunk:
            if MODE == "old":
                results.append(app.record_event(client, database, cache, "render", event, now))
            else:
                results.append(app.record_event(database, cache, "render", event, now))

    workers = [threading.Thread(target=record, args=(events[t::THREADS],)) for t in range(THREADS)]
    ready.set()
    started = time.perf_counter()
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    recorded_at = time.perf_counter() - started

    if MODE == "new":
        while database.inbox.count_documents({"folded": False}):
            time.sleep(0.005)
    counted_at = time.perf_counter() - started
    stop.set()
    if folder:
        folder.join()

    rendered = sum(row.get("render", 0) for row in database.reports.find())
    total = database.spend.find_one({"_id": "ad:AD1"}) if SHAPE == "one" else None
    spent = total["nanos"] if total else None
    outcomes = {name: results.count(name) for name in set(results)}
    folds = list(fold_log)
    fold_text = ""
    if folds:
        fold_text = (
            f" folds={len(folds)} fold_sizes={[size for size, _ in folds][:6]} "
            f"fold_secs={[round(secs, 2) for _, secs in folds][:6]} fold_attempts={fold_attempts.value}"
        )
    print(
        f"mode={MODE} shape={SHAPE} recorded_in={recorded_at:.2f}s counted_in={counted_at:.2f}s "
        f"rate={N / counted_at:.0f}/s attempts_per_event={attempts.n / N:.2f} render_total={rendered} "
        f"outcomes={outcomes} spend_ok={spent == N * price if SHAPE == 'one' else 'n/a'}{fold_text}"
    )
    client.drop_database(dbname)


if __name__ == "__main__":
    main()
