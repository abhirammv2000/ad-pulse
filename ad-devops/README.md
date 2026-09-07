# ad-devops

Deployment code for Ad Pulse.

- `helm/ad-pulse/` — the Kubernetes chart for every service. Credentials are
  never stored in `values.yaml`; they're supplied to `templates/secrets.yaml`
  via a values file you don't commit or `--set-string` from CI secrets. See
  the top-level [README](../README.md#deploying) for the full list.
- `deployments/docker-compose.yaml` — a Kafka + Zookeeper compose file. Nothing
  in the current services talks to Kafka (the engagement pipeline runs on GCP
  Pub/Sub — see the top-level README); this predates that and is unused.
- `deployments/*.yaml` — older plain-manifest deployments, superseded by the
  Helm chart; kept for reference.

## Quick deploy

```
helm upgrade --install adpulse ./helm/ad-pulse \
  --namespace adpulse --create-namespace \
  -f my-values-secrets.yaml
```

`my-values-secrets.yaml` supplies `adpulse.secrets.*` (see
`helm/ad-pulse/values.yaml` for the full key list) and is not checked in.
