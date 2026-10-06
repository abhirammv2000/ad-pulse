# ad-devops

Deployment code for Ad Pulse.

- `helm/ad-pulse/`: the Kubernetes chart for every service. Credentials are
  never stored in `values.yaml`; they're supplied to `templates/secrets.yaml`
  via a values file you don't commit or `--set-string` from CI secrets. See
  the top-level [README](../README.md#deploying) for the full list.
- `deployments/docker-compose.yaml`: the full local stack (Postgres, Redis,
  MongoDB, a Pub/Sub emulator and all six services). Kafka is not used
  anywhere; the engagement pipeline runs on GCP Pub/Sub, see the top-level
  README.

## Quick deploy

```
helm upgrade --install adpulse ./helm/ad-pulse \
  --namespace adpulse --create-namespace \
  -f my-values-secrets.yaml
```

`my-values-secrets.yaml` supplies `adpulse.secrets.*` (see
`helm/ad-pulse/values.yaml` for the full key list) and is not checked in.
