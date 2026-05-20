# Running a Nautobot Job on a Local Kubernetes Cluster

This guide walks through running a Nautobot Job inside a Kubernetes job pod, with the rest of the Nautobot development stack (Django app, Postgres, Redis) running locally in Docker Compose.

The high-level setup looks like this:

- **Nautobot web app** runs in Docker Compose on your host.
- **Postgres and Redis** run in Docker Compose on your host and are exposed on host ports.
- **Kubernetes cluster** runs on your host via Docker Desktop.
- When a job is dispatched, Nautobot calls the Kubernetes API and creates a **job pod inside the cluster**. That pod connects back to the host's Postgres and Redis through `host.docker.internal`.

Both "sides" share the same database, so the `JobResult` row created by the Nautobot web app is visible to the job pod.

## Prerequisites

- Docker Desktop with Kubernetes enabled.
- `kubectl` configured and pointing to your local cluster (`kubectl get nodes` should return one node).

## Expose Postgres and Redis on host ports

By default the dev compose file exposes Postgres and Redis only inside the Compose network. The Kubernetes job pod cannot reach them there, so we need to publish them on the host.

Edit `development/docker-compose.postgres.yml` and add a `ports` mapping:

```yaml
services:
  db:
    image: postgres:14
    env_file:
      - dev.env
    ports:
      - "5432:5432"   # <-- ADD
    volumes:
      - pgdata_nautobot:/var/lib/postgresql/data
```

Do the same for Redis edit `development/docker-compose.yml`:

```yaml
    redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"    # <-- ADD
```

## Update the `dev-env` ConfigMap

The job pod uses environment variables from the `dev-env` ConfigMap to find the database and Redis. By default they point at the Kubernetes-internal service names `db` and `redis`. Since we are pointing the pod at the host's Postgres and Redis instead, change both to `host.docker.internal`.

In `development/kubernetes/dev-env-configmap.yaml`:

```yaml
data:
  NAUTOBOT_DB_HOST: host.docker.internal     # was: db
  NAUTOBOT_REDIS_HOST: host.docker.internal  # was: redis
```

> **Why `host.docker.internal`?**
> Inside the cluster, `127.0.0.1` resolves to the pod itself, not your host. `host.docker.internal` is the DNS name that Docker Desktop provide for "the machine running the container runtime".

Apply the change:

```bash
kubectl apply -f development/kubernetes/dev-env-configmap.yaml
```

## (Optional) Enable apps in `nautobot-cm1`

If your jobs live in a Nautobot app such as `example_app`, uncomment it in the ConfigMap so the job pod also loads the app:

```yaml
PLUGINS = [
    "example_app",   # was: # "example_app",
]
```

Then apply:

```bash
kubectl apply -f development/kubernetes/nautobot-cm1-configmap.yaml
```

## Create the PersistentVolumeClaims

The job pod mounts a PVC named `media-root` for `/opt/nautobot/media`. Apply the PVC manifests before starting any jobs:

```bash
kubectl apply -f "development/kubernetes/*-persistentvolumeclaim.yaml"
```

Expected output:

```text
persistentvolumeclaim/media-root created
persistentvolumeclaim/pgdata-nautobot created
```

## Force the job pod to use the locally built image

The job manifest references `local/nautobot-dev:local-3.2-py3.13`. That image only exists in your local image store. To make sure the pod uses the freshly built local image (and never tries to pull from a registry), add `imagePullPolicy: Always` to the container spec in `KUBERNETES_JOB_MANIFEST` inside `nautobot_config.py` (and in `nautobot-cm1` if you keep both in sync):

```python
"containers": [
    {
        "name": "nautobot-job",
        "image": "local/nautobot-dev:local-3.2-py3.13",
        "imagePullPolicy": "Always",   # <-- ADD
        ...
    }
]
```

## Point Nautobot at the host's Kubernetes API

Inside the Compose container, `127.0.0.1` is the container, not the host. So even though `kubectl config view` shows the cluster as `https://127.0.0.1:50675`, the Nautobot container needs the host-routable form.

Set in your `dev.env` (or wherever you configure Nautobot):

```bash
NAUTOBOT_KUBERNETES_DEFAULT_SERVICE_ADDRESS=https://host.docker.internal:50675
```

Find the port from your kubeconfig:

```bash
kubectl config view
```

Look for the `server:` line under your cluster — the port (`50675` in this example) is assigned by Docker Desktop and may differ on your machine. The hostname **is not** what you copy verbatim — you replace `127.0.0.1` with `host.docker.internal` because the request originates from inside the Nautobot container, not from the host.

## Create a service account and a long-lived token

```bash
# Service account
kubectl create serviceaccount nautobot-sa -n default

# Permissions
kubectl create clusterrolebinding nautobot-sa-binding \
  --clusterrole=cluster-admin \
  --serviceaccount=default:nautobot-sa

kubectl create token nautobot-sa --duration=8760h > /tmp/k8s-token
```

Tell Nautobot where to find the token (in `dev.env` or equivalent):

```bash
NAUTOBOT_KUBERNETES_TOKEN_PATH=/tmp/k8s-token
```

mount the token as a volume in `docker-compose.yml`:

```yaml
 volumes:
   - /tmp/k8s-token:/tmp/k8s-token:ro
```

## Disable SSL verification in the Kubernetes client code

The local cluster's TLS certificate is issued for `127.0.0.1` / `kubernetes.default.svc`, **not** for `host.docker.internal`. Because we connect via `host.docker.internal`, the hostname does not match and verification fails. For local development we disable verification.

In the relevant function (e.g. `create_kubernetes_job` in `nautobot/extras/jobs.py` or wherever your project keeps it), comment out the CA cert assignment and turn off SSL verification:

```python
def create_kubernetes_job():
    configuration = kubernetes.client.Configuration()
    configuration.host = settings.KUBERNETES_DEFAULT_SERVICE_ADDRESS
    # configuration.ssl_ca_cert = pod_ssl_ca_cert   # <-- COMMENT OUT for local dev
    configuration.verify_ssl = False                # <-- ADD for local dev
    with open(pod_token, "r", encoding="utf-8") as token_file:
        token = token_file.read().strip()
    configuration.api_key_prefix["authorization"] = "Bearer"
    configuration.api_key["authorization"] = token
    ...
```

## Start Nautobot and run a job

With all the configuration in place, bring up the Nautobot stack:

```bash
invoke start
```

or, if you want to attach a debugger to the Django process:

```bash
invoke debug
```

Then:

1. Open Nautobot at `http://localhost:8080`.
2. Navigate to **Jobs**, pick a job (e.g. one from `example_app`), and run it. (For the job to actually be dispatched to Kubernetes (rather than running in the regular Celery worker), it needs to be assigned to a job queue of type **Kubernetes**. See [Configure a New Job Queue of Type Kubernetes](../../user-guide/platform-functionality/jobs/kubernetes-job-support.md#configuration) for how to create the queue and route a job to it.)
3. Watch the cluster react:

    ```bash
    kubectl get all
    ```

    You should see a pod named `nautobot-job-<job_result_uuid>-<suffix>` appear and progress through `Pending` - `ContainerCreating` - `Running` - `Completed`.

4. Inspect what the pod did:

    ```bash
    kubectl logs <pod-name>
    ```

5. Check the **Job Results** page in the Nautobot UI. The result should be marked successful and contain the log output.
