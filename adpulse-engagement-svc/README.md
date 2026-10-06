# adpulse-engagement-svc

Go/Gin service behind the click and render tracking URLs ad-server-svc embeds
in every bid. `GET /engagement/clk` and `GET /engagement/csc` both take an
`iid` query parameter (base64-encoded JSON identifying the ad, creative,
campaign and advertiser), validate it, and publish it to the matching Pub/Sub
topic for adpulse-engagement-subscriber-svc to aggregate.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GCP_PROJECT_ID` | none (required) | Pub/Sub project |
| `GOOGLE_APPLICATION_CREDENTIALS` | none | Path to a service account key; unset in the cluster where Workload Identity applies instead |
| `CLICK_TOPIC_ID` | `click-service-topic` | Pub/Sub topic clicks are published to |
| `CSC_TOPIC_ID` | `csc-service-topic` | Pub/Sub topic renders are published to |
| `SERVER_ADDRESS` | `:8081` | Address to listen on |

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
