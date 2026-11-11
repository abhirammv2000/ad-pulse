"""Load test of the serve path and the budget check, against the Compose stack.

It creates one CPM ad with a budget, asks for it from several threads as fast as
they can go, renders every ad it is served the way a page would, and keeps going
until the ad stops serving because its budget is spent. Then it waits for the last
renders to be counted and reports the latency, and how far the real spend went past
the budget: the in-flight overspend the ad server README describes.

    AD_MANAGER_HOST=http://localhost:5000 AD_SERVER_HOST=http://localhost:8080 \
      AD_MANAGER_API_KEY=local-dev-api-key python loadtest.py

THREADS, BUDGET (USD) and MAX_SECONDS change the defaults below.

Two things change the result. The campaign it creates has a $10 daily budget, which the ad
server paces over the UTC day with an hour of headroom, so early in the UTC day the campaign
may be allowed to spend less than BUDGET and the ad stops at that smaller amount (about $1.22
at 01:55 UTC). And every run leaves its campaign behind, so the ad server walks more
campaigns on each request and latency creeps up. The "latency" line is mostly this and the
Python client, not the ad server's own work.
"""

import copy
import os
import statistics
import threading
import time
import uuid

import requests

from integration_test import FLIGHT_END, FLIGHT_START, TestAPI, ad_serve_payload

THREADS = int(os.getenv("THREADS", "16"))
BUDGET = float(os.getenv("BUDGET", "1"))  # USD
BID = 1.0  # a $1 CPM bid pays $0.001 a render
MAX_SECONDS = float(os.getenv("MAX_SECONDS", "120"))


def percentile(values, share):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def main():
    # The integration test already knows how to create every entity, so use its helpers.
    setup = TestAPI('test_workflow')
    setup.setUp()
    publisher_id = setup._create_publisher()
    advertiser_id = setup._create_advertiser()
    ad_unit_id = setup._create_ad_unit(publisher_id)
    campaign_id = setup._create_active_campaign(advertiser_id)
    creative_id = setup._create_creative(advertiser_id)
    ad = setup.manager.post(setup.ad_manager_host + '/ad', json={
        "ad_unit_targeted": [ad_unit_id], "adname": "Load test ad", "adpriority": 1, "adtype": "NON_GUARANTEED",
        "advertiserid": advertiser_id, "campaignid": campaign_id, "creativeid": creative_id,
        "bidinfo": {"bid": BID, "bidType": "CPM"}, "budget": {"currencyCode": "USD", "totalBudget": BUDGET},
        "startdate": FLIGHT_START, "enddate": FLIGHT_END, "landingurl": "example.com",
        "createdby": "loadtest", "updatedby": "loadtest",
    }).json()['ad']
    setup.manager.patch(setup.ad_manager_host + '/ad', params={'ad_id': ad['adid'], 'state': 'ACTIVE'})
    setup._refresh_cache()

    params = {'adunit_id': ad_unit_id, 'publisher_id': publisher_id}
    stop = threading.Event()
    lock = threading.Lock()
    latencies = {200: [], 204: []}
    last_bid_at = [time.time()]
    renders_sent = [0]

    def worker():
        session = requests.Session()
        payload = copy.deepcopy(ad_serve_payload)
        while not stop.is_set():
            payload['user']['id'] = uuid.uuid4().hex
            start = time.perf_counter()
            response = session.post(setup.ad_server_host + '/adserve', params=params, json=payload)
            took = time.perf_counter() - start
            with lock:
                latencies.setdefault(response.status_code, []).append(took)
            if response.status_code == 200:
                with lock:
                    last_bid_at[0] = time.time()
                session.get(response.json()['bid'][0]['ext']['renderUrl'])
                with lock:
                    renders_sent[0] += 1

    started = time.time()
    threads = [threading.Thread(target=worker) for _ in range(THREADS)]
    for thread in threads:
        thread.start()
    # Run until nothing has been served for three seconds: the budget is spent and the ad server knows it.
    while time.time() - started < MAX_SECONDS:
        time.sleep(0.5)
        with lock:
            if latencies[200] and time.time() - last_bid_at[0] > 3:
                break
    stop.set()
    for thread in threads:
        thread.join()
    served_for = last_bid_at[0] - started

    # Wait for the last renders to be counted: the count has to hold still for five seconds.
    counted, still_since = -1, time.time()
    while time.time() - still_since < 5:
        rows = setup.manager.get(setup.ad_manager_host + '/reports/' + ad['adid']).json()
        now_counted = rows[0]['render'] if rows else 0
        if now_counted != counted:
            counted, still_since = now_counted, time.time()
        time.sleep(1)

    spend = counted * BID / 1000
    budget_renders = round(BUDGET * 1000 / BID)
    bids, no_bids = latencies[200], latencies.get(204, [])
    every = bids + no_bids
    print(f"threads                 {THREADS}")
    print(f"requests                {len(every)} in {served_for:.1f} s of serving "
          f"({len(bids) / served_for:.0f} bids/s), then {len(no_bids)} answered with no bid")
    print(f"latency, every request  p50 {percentile(every, .5) * 1000:.1f} ms  p95 {percentile(every, .95) * 1000:.1f} ms  "
          f"p99 {percentile(every, .99) * 1000:.1f} ms  mean {statistics.mean(every) * 1000:.1f} ms")
    print(f"renders sent / counted  {renders_sent[0]} / {counted}")
    print(f"budget                  ${BUDGET:.3f} ({budget_renders} renders)")
    print(f"spent                   ${spend:.3f} ({counted} renders)")
    print(f"overspend               ${spend - BUDGET:.3f} ({counted - budget_renders} renders, "
          f"{(spend - BUDGET) / BUDGET * 100:.1f}% of the budget)")
    other = {code: len(v) for code, v in latencies.items() if code not in (200, 204) and v}
    if other:
        print(f"other answers           {other}")

    setup.manager.patch(setup.ad_manager_host + '/ad', params={'ad_id': ad['adid'], 'state': 'INACTIVE'})


if __name__ == '__main__':
    main()
