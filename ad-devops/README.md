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

## Deploy to GKE

This is the procedure that was run on 2026-11-10 (results in
[docs/DESIGN.md](../docs/DESIGN.md#10-capacity-and-a-measured-run)). It creates billable
resources, roughly $0.25 an hour while it is up, so tear it down when you are done. Set
`PROJECT_ID`, `REGION` (us-central1 here) and `TAG` (the commit you built) first.

```
# 1. The images, in Artifact Registry.
gcloud artifacts repositories create adpulse --repository-format=docker --location=$REGION
gcloud auth configure-docker $REGION-docker.pkg.dev
for d in ad-manager-svc ad-manager-frontend ad-server-svc adpulse-engagement-svc \
         adpulse-engagement-subscriber-svc ad-refresh-cache-svc; do
  docker build --platform linux/amd64 -t $REGION-docker.pkg.dev/$PROJECT_ID/adpulse/$d:$TAG $d
  docker push $REGION-docker.pkg.dev/$PROJECT_ID/adpulse/$d:$TAG
done

# 2. Postgres and Redis on a private range of the default network.
gcloud compute addresses create adpulse-psa --global --purpose=VPC_PEERING --prefix-length=20 --network=default
gcloud services vpc-peerings connect --service=servicenetworking.googleapis.com --ranges=adpulse-psa --network=default
gcloud sql instances create adpulse-pg --database-version=POSTGRES_16 --edition=ENTERPRISE --tier=db-f1-micro \
  --region=$REGION --network=default --no-assign-ip --storage-size=10 --no-backup
gcloud sql databases create adpulse --instance adpulse-pg
gcloud sql users create adpulse --instance adpulse-pg --password "$DB_PASSWORD"
gcloud redis instances create adpulse-redis --size=1 --tier=basic --region=$REGION --network=default

# 3. The cluster, with Workload Identity on, and MongoDB as a replica set in it.
gcloud container clusters create adpulse --zone ${REGION}-a --num-nodes 2 --machine-type e2-standard-2 \
  --workload-pool=$PROJECT_ID.svc.id.goog --enable-ip-alias
gcloud container clusters get-credentials adpulse --zone ${REGION}-a
kubectl apply -f ad-devops/gke/mongo.yaml
kubectl create namespace adpulse

# 4. Pub/Sub, and the only two permissions the services need, bound to their Kubernetes service accounts.
PRINCIPAL=principal://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$PROJECT_ID.svc.id.goog/subject/ns/adpulse/sa
for t in click-service-topic csc-service-topic; do
  gcloud pubsub topics create $t
  gcloud pubsub subscriptions create $t-sub --topic $t --ack-deadline 60
  gcloud pubsub topics add-iam-policy-binding $t --role=roles/pubsub.publisher \
    --member="$PRINCIPAL/adpulse-engagement-svc-service-account"
  gcloud pubsub subscriptions add-iam-policy-binding $t-sub --role=roles/pubsub.subscriber \
    --member="$PRINCIPAL/adpulse-engagement-subscriber-svc-service-account"
done
```

Then install the chart. `values-gke.yaml` has the image names, Pub/Sub on real Google Cloud
(`pubsubEmulatorHost` empty) and the MongoDB address; replace `PROJECT_ID` and `TAG` in it. The
database and Redis addresses are the private IPs from steps 2, and the secrets are generated,
not stored. The LoadBalancer addresses only exist after the first install, so install twice:
once with placeholders, then again with the public addresses.

```
helm upgrade --install adpulse ad-devops/helm/ad-pulse --namespace adpulse -f ad-devops/gke/values-gke.yaml \
  --set ad_engagement_svc_clk=$ENGAGEMENT/engagement/clk --set ad_engagement_svc_rndr=$ENGAGEMENT/engagement/csc \
  --set ad_server_url=$AD_SERVER --set dashboard_manager_url=$MANAGER \
  --set-string adpulse.secrets.databaseUrl="postgresql://adpulse:$DB_PASSWORD@$SQL_PRIVATE_IP:5432/adpulse" \
  --set-string adpulse.secrets.redisHost=$REDIS_IP \
  --set-string adpulse.secrets.trackingSecret=$(openssl rand -hex 32) \
  --set-string adpulse.secrets.managerApiKey=$MANAGER_API_KEY \
  --wait --timeout 10m
helm test adpulse --namespace adpulse
AD_MANAGER_HOST=$MANAGER AD_SERVER_HOST=$AD_SERVER AD_MANAGER_API_KEY=$MANAGER_API_KEY \
  python -m unittest integration_test -v
```

`kubectl get svc --namespace adpulse` shows the public addresses for `$MANAGER` (port 5000),
`$AD_SERVER` (8080) and `$ENGAGEMENT` (8081), written as `http://<address>:<port>`. These are
plain HTTP on public addresses with one shared API key, which is fine for a test that lasts
a couple of hours and is not how a real deployment should be exposed. MongoDB is a single
member, so it has no failover.

**Tear down**, in this order, then list each resource type to check nothing is left: `helm
uninstall`, the MongoDB StatefulSet and its disk (`kubectl delete -f ad-devops/gke/mongo.yaml`
and `kubectl delete pvc --all -n adpulse-data`), the cluster, the Cloud SQL and Redis
instances, the Pub/Sub topics and subscriptions, the Artifact Registry repository, and last
the VPC peering and the `adpulse-psa` range. The peering can refuse to delete for a while after
Cloud SQL and Redis are gone, because Google releases its side later. It costs nothing.
