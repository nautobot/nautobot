# Running a Nautobot Job on a Local Kubernetes Cluster

This guide walks through running a Nautobot Job inside a Kubernetes job pod, with the rest of the Nautobot development stack (Django app, Postgres, Redis) running locally in Docker Compose.

The high-level setup looks like this:

- **Nautobot web app** runs in Docker Compose on your host.
- **Postgres and Redis** run in Docker Compose on your host and are exposed on host ports.
- **Kubernetes cluster** runs on your host via Docker Desktop.
- When a job is dispatched, Nautobot calls the Kubernetes API and creates a **job pod inside the cluster**. That pod connects back to the host's Postgres and Redis through `host.docker.internal`.

Both "sides" share the same database, so the `JobResult` row created by the Nautobot web app is visible to the job pod.

## Prerequisites

- Docker Desktop version `4.72.0` or higher installed.
- `kubectl` installed and available on your `$PATH`.

### Create a local Kubernetes cluster

On a fresh Docker Desktop install there is no cluster yet, so `kubectl get nodes` will fail with:

```text
error: current-context is not set
```

Create one through the Docker Desktop UI:

1. Open **Docker Desktop → Settings → Kubernetes**.
2. Click **Create cluster**, pick provisioner **kind** with **1 node**, and confirm.
3. Wait for Docker Desktop to report Kubernetes as running.
Verify the cluster is up and that `kubectl` is pointing at it:

```bash
kubectl config current-context   # should print: docker-desktop
kubectl get nodes                # should list one Ready node
```

If `current-context` prints something else, switch to it:

```bash
kubectl config use-context docker-desktop
```

## Create a service account and a long-lived token

```bash
# Service account
kubectl create serviceaccount nautobot-sa -n default

# Permissions
kubectl create clusterrolebinding nautobot-sa-binding \
  --clusterrole=cluster-admin \
  --serviceaccount=default:nautobot-sa

kubectl create token nautobot-sa --duration=8760h > <path_to_your_k8s_token>
```

Tell Nautobot where to find the token (in `dev.env` or equivalent):

```bash
NAUTOBOT_KUBERNETES_TOKEN_PATH="/tmp/k8s-token"
```

mount the token as a volume in `docker-compose.yml`

```yaml
 services:
  nautobot:
    secrets:
        - k8s_token
    build:
      args:
        PYTHON_VER: "${PYTHON_VER}"
      context: ../
      dockerfile: docker/Dockerfile
      target: dev
    healthcheck:
      start_period: 10m
    image: "local/nautobot-dev:local-${NAUTOBOT_VER}-py${PYTHON_VER}"
    ports:
      - "8080:8080"
    volumes:
      - media_root:/opt/nautobot/media
      - <path_to_your_k8s_token>:/tmp/k8s-token:ro # <-- ADD
```

or just use `docker-compose.k8s.yml` and change only <path_to_your_k8s_token>:

```yaml
services:
  nautobot:
    secrets:
        - k8s_token
    build:
      args:
        PYTHON_VER: "${PYTHON_VER}"
      context: ../
      dockerfile: docker/Dockerfile
      target: dev
    healthcheck:
      start_period: 10m
    image: "local/nautobot-dev:local-${NAUTOBOT_VER}-py${PYTHON_VER}"
    ports:
      - "8080:8080"
    volumes:
      - media_root:/opt/nautobot/media
      - <path_to_your_k8s_token>:/tmp/k8s-token:ro # <-- CHANGE
```

## Expose Postgres and Redis on host ports

By default the dev compose file exposes Postgres and Redis only inside the Compose network. The Kubernetes job pod cannot reach them there, so we need to publish them on the host.

So please use `development/docker-compose.k8s.postgres.yml` insted of `development/docker-compose.postgres.yml` and `development/docker-compose.k8s.yml` instead of `development/docker-compose.yml` or just do below changes.

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

## (Optional) Enable apps in `development/kubernetes/nautobot-cm1-configmap.yaml`

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

To make sure the pod picks up the latest build every time, set `imagePullPolicy: Always` on the container spec in `KUBERNETES_JOB_MANIFEST` inside `nautobot_config.py` (and in `development/kubernetes/nautobot-cm1-configmap.yaml` if you keep both in sync).

Before editing the manifest, check what your locally built image is actually tagged as. The tag in the manifest may be out of date and won't match what `invoke build` produced on your machine. Build first:

```bash
invoke build
```

Then copy the tag that matches the `local/nautobot-dev:...` and paste into the manifest and add `imagePullPolicy: Always`:

```python
"containers": [
    {
        "name": "nautobot-job",
        "image": "local/nautobot-dev:local-3.2-py3.13", # <-- use the tag from `docker images`
        "imagePullPolicy": "Always",   # <-- ADD
        ...
    }
]
```

While you're editing the manifest, bump `ttlSecondsAfterFinished` for development. The default in the manifest is very short (a few seconds), which means Kubernetes garbage-collects the finished Job and its pod before you can inspect it with `kubectl logs`. Set it to something like 300 (5 minutes) so completed jobs stick around long enough to debug:

```python
"spec": {
    "ttlSecondsAfterFinished": 300,   # <-- bump from the default
    "template": {
        ...
    },
    ...
}
```

## Point Nautobot at the host's Kubernetes API

Inside the Compose container, `127.0.0.1` is the container, not the host. So even though `kubectl config view` shows the cluster as `https://127.0.0.1:50675`, the Nautobot container needs the host-routable form.

Find the port from your kubeconfig:

```bash
kubectl config view
```

Look for the `server:` line under your cluster — the port (`50675` in this example) is assigned by Docker Desktop and may differ on your machine. The hostname **is not** what you copy verbatim — you replace `127.0.0.1` with `host.docker.internal` because the request originates from inside the Nautobot container, not from the host.

Set in your `dev.env` (or wherever you configure Nautobot):

```bash
NAUTOBOT_KUBERNETES_DEFAULT_SERVICE_ADDRESS=https://host.docker.internal:50675
```

## Disable SSL verification in the Kubernetes client code

The local cluster's TLS certificate is issued for `127.0.0.1` / `kubernetes.default.svc`, **not** for `host.docker.internal`. Because we connect via `host.docker.internal`, the hostname does not match and verification fails. For local development we disable verification.

In the function (`build_kubernetes_api_client` in `nautobot/extras/utils.py`), comment out the CA cert assignment and turn off SSL verification:

```python
def build_kubernetes_api_client():
    """Build an authenticated ApiClient using the in-cluster service account."""
    configuration = kubernetes.client.Configuration()
    configuration.host = settings.KUBERNETES_DEFAULT_SERVICE_ADDRESS
    # configuration.ssl_ca_cert = settings.KUBERNETES_SSL_CA_CERT_PATH # <-- COMMENT OUT for local dev
    configuration.verify_ssl = False                                   # <-- ADD for local dev
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
