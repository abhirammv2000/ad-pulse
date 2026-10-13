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

## Try the chart on a local Kubernetes cluster

This runs the real chart with no cloud account, on Docker Desktop's Kubernetes (enable it in
Docker Desktop's settings). Postgres, Redis, MongoDB and a Pub/Sub emulator run in the cluster as
stand-ins for the managed services a real deployment uses. It needs about 4 GB of memory for
Docker. From the repository root:

```
# 1. Build the six images. They are used from the local image store, so nothing is pushed.
for d in ad-manager-svc ad-refresh-cache-svc ad-server-svc adpulse-engagement-svc \
         adpulse-engagement-subscriber-svc ad-manager-frontend; do
  docker build -t adpulse-local/$d:test $d
done

# 2. The dependencies, in their own namespace.
kubectl create namespace adpulse-verify
kubectl apply -f ad-devops/local-k8s/deps.yaml
kubectl -n adpulse-verify wait --for=condition=available deployment --all --timeout=300s
kubectl -n adpulse-verify wait --for=condition=complete job/pubsub-init --timeout=240s

# 3. The chart.
helm upgrade --install adpulse ad-devops/helm/ad-pulse --namespace adpulse-verify \
  -f ad-devops/local-k8s/values-local.yaml --wait --timeout 300s

# 4. Check it from inside the cluster, then run the end-to-end test against it.
helm test adpulse --namespace adpulse-verify
AD_MANAGER_HOST=http://localhost:5000 AD_SERVER_HOST=http://localhost:8080 \
  AD_MANAGER_API_KEY=local-dev-api-key python -m unittest integration_test -v

# 5. Remove everything.
helm uninstall adpulse --namespace adpulse-verify
kubectl delete namespace adpulse-verify
```

Docker Desktop publishes each LoadBalancer Service on localhost, so the dashboard is on
http://localhost:3000 (its service URLs there are the in-cluster names, so it is only useful for
checking that the pod serves; use the Compose stack to click around). If your `kubectl` points at
another cluster, add `--context docker-desktop` to every `kubectl` and `--kube-context docker-desktop`
to every `helm` command.

**What this proves and what it does not.** On 2026-10-13 this exact procedure brought all six
services up and passed `helm test` and the end-to-end test (create, cache, serve, click, render,
report) on Docker Desktop's Kubernetes 1.30. It does not cover a real cloud: managed databases,
Google credentials for Pub/Sub (set `serviceAccount.annotations` for Workload Identity and leave
`pubsubEmulatorHost` empty), public addresses, or the deploy workflows.
