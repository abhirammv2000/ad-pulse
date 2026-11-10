# adpulse-engagement-svc

Go/Gin service behind the click and render tracking URLs ad-server-svc embeds
in every bid. `GET /engagement/clk` and `GET /engagement/csc` both take an
`iid` query parameter (base64-encoded JSON identifying the bid, ad, creative,
campaign and advertiser, and when it was served), validate it, and publish it to
the matching Pub/Sub topic for adpulse-engagement-subscriber-svc to count.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GCP_PROJECT_ID` | none (required) | Pub/Sub project |
| `GOOGLE_APPLICATION_CREDENTIALS` | none | Path to a service account key; unset in the cluster where Workload Identity applies instead |
| `CLICK_TOPIC_ID` | `click-service-topic` | Pub/Sub topic clicks are published to |
| `CSC_TOPIC_ID` | `csc-service-topic` | Pub/Sub topic renders are published to |
| `SERVER_ADDRESS` | `:8081` | Address to listen on |
| `TRACKING_SECRET` | none | When set, every click and render URL must carry a valid `sig`, or the answer is 403. Use the same value as ad-server-svc. When empty, URLs are not checked and the service logs a warning at startup |

## Signed URLs

ad-server-svc adds `&sig=<hex>` to each URL, where the signature is the
HMAC-SHA256 of the `iid` text with `TRACKING_SECRET`. This service recomputes
it and compares in constant time. Without that, anyone could invent an `iid`
and add clicks to any ad.

A signature does not stop someone opening a real URL many times. That is handled
downstream: the iid carries the bid id, and adpulse-engagement-subscriber-svc counts
each bid's click and render at most once.

## Serve time

The iid also carries `requesttimestamp`, when the ad server served the bid. An
event whose ad was served more than 24 hours ago gets `410 Gone`, and one served
more than 5 minutes in the future (clocks that disagree by more than that) gets a
400. An iid without a `bidid` or a serve time is a 400. The 24 hours fit the
subscriber's limits, which are what stop a late replay from being counted twice.
See its README.

## Metrics

`GET /metrics` serves `engagement_events_total{event, result}`: each click and render ping by
what happened to it (accepted, bad_signature, too_old, bad_request, publish_failed, error).

## Running

```
export GCP_PROJECT_ID=your-project
gcloud auth application-default login   # or set GOOGLE_APPLICATION_CREDENTIALS
go run main.go
```

## Testing

```
go test ./...
```

`services/engagement_test.go` exercises the handlers against a fake
`Publisher`, so the tests need no GCP project or credentials.
