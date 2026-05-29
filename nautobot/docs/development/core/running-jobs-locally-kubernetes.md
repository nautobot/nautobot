# Running a Nautobot Job on a Local Kubernetes Cluster

This guide walks through running a Nautobot Job inside a Kubernetes job pod, with the rest of the Nautobot development stack (Django app, Postgres, Redis) running locally in Docker Compose.

The high-level setup looks like this:

- **Nautobot web app** runs in Docker Compose on your host.
- **Postgres and Redis** run in Docker Compose on your host and are exposed on host ports.
- **Kubernetes cluster** runs on your host via Docker Desktop.
- When a job is dispatched, Nautobot calls the Kubernetes API and creates a **job pod inside the cluster**. That pod connects back to the host's Postgres and Redis through `host.docker.internal`.

Both "sides" share the same database, so the `JobResult` row created by the Nautobot web app is visible to the job pod.

## Prerequisites

- Docker Desktop version `4.64` or higher installed. The instructions below assume the Kubernetes setup flow available in `4.64+` (UI may differ in older versions, so steps may not match exactly).
- `kubectl` installed and available on your `$PATH`.
- Kubernetes version: any version Docker Desktop ships with should work. This guide was verified against `1.34.3`

### Create a local Kubernetes cluster

On a fresh Docker Desktop install there is no cluster yet, so `kubectl get nodes` will fail with:

```text
error: current-context is not set
```

Create one through the Docker Desktop UI:

1. Open **Docker Desktop → Settings → Kubernetes**.
2. Click **Create cluster**, pick provisioner **kind** with **1 node** and default `1.34.3` kubernetes version and confirm.
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

The token is valid for one year (`8760h`). To verify it still valid you can check `exp` from:

```bash
jq -R 'split(".") | .[0],.[1] | @base64d | fromjson' < <path_to_your_k8s_token>
```

example output:

```json
  {
    "alg": "RS256",
    "kid": ...
  }
  {
    "aud": [
      "https://kubernetes.default.svc.cluster.local"
    ],
    "exp": 1779452794,
    "iat": 1779452194,
    "iss": "https://kubernetes.default.svc.cluster.local",
    ...
  }
```

If token expired - re-run the `kubectl create token ...` command above to overwrite the file with a fresh one.

## Wire up the local-development Compose overrides

The k8s-specific changes (token mount, host-side Postgres and Redis ports) all live in dedicated override files so the shared compose files stay untouched:

- `development/docker-compose.k8s.yml` — exposes Redis on the host and mounts the token into the Nautobot container.
- `development/docker-compose.postgres.k8s.yml` — exposes Postgres on the host.

Add both to the `compose_files` list in your local `development/invoke.yml`, in the order shown below (each k8s override must come **after** the base file it extends):

```yaml
nautobot:
  compose_files:
    - "docker-compose.yml"
    - "docker-compose.k8s.yml"          # <-- ADD: extends docker-compose.yml
    - "docker-compose.postgres.yml"
    - "docker-compose.postgres.k8s.yml" # <-- ADD: extends docker-compose.postgres.yml
    - "docker-compose.dev.yml"
```

From now on, all `invoke` commands automatically include the k8s overrides.

## Apply the local-development ConfigMap override

The job pod reads its database and Redis hosts from the `dev-env` ConfigMap. By default that ConfigMap targets the Kubernetes-internal service names `db` and `redis`, but in this setup Postgres and Redis run on the host (via Docker Compose), not in the cluster, so the pod needs `host.docker.internal` instead.

A ready-made patch file is provided at `development/kubernetes/dev-env-local-patch.yaml` that overrides only the two host entries. Apply the base ConfigMap first, then patch it:

```bash
kubectl apply -f development/kubernetes/dev-env-configmap.yaml
kubectl patch configmap dev-env --patch-file development/kubernetes/dev-env-local-patch.yaml
```

The patch contents:

```yaml
data:
  NAUTOBOT_DB_HOST: host.docker.internal
  NAUTOBOT_REDIS_HOST: host.docker.internal
```

Verify all original keys are still present after the patch:

```bash
kubectl describe configmap dev-env
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

## Disable SSL verification

The local cluster's TLS certificate is issued for `127.0.0.1` / `kubernetes.default.svc`, **not** for `host.docker.internal`. Because we connect via `host.docker.internal`, the hostname does not match and verification fails. For local development we disable verification.

Set the internal override in your `dev.env`:

```bash
NAUTOBOT_KUBERNETES_VERIFY_SSL_INTERNAL=false
```

## Start Nautobot and run a job

With all the configuration in place, bring up the Nautobot stack:

```bash
invoke start \
  -e SRC_KUBERNETES_TOKEN_LOCAL_PATH=<path_to_your_k8s_token> \
  -e DESC_KUBERNETES_TOKEN_PATH=$NAUTOBOT_KUBERNETES_TOKEN_PATH
```

Or, if you want to attach a debugger to the Django process:

```bash
invoke debug \
  -e SRC_KUBERNETES_TOKEN_LOCAL_PATH=<path_to_your_k8s_token> \
  -e DESC_KUBERNETES_TOKEN_PATH=$NAUTOBOT_KUBERNETES_TOKEN_PATH
```

- `SRC_KUBERNETES_TOKEN_LOCAL_PATH` — absolute path on your host where you saved the token (the file produced by `kubectl create token`).
- `DESC_KUBERNETES_TOKEN_PATH` — name of the env var inside the container that points at the mounted token; should match `NAUTOBOT_KUBERNETES_TOKEN_PATH` from `dev.env`.

Then:

1. Open Nautobot at `http://localhost:8080`.
2. Create new queue type kubernetes: Left nav → Jobs → Job Queues → + → Name: kubernetes, Queue Type: Kubernetes → Create
3. Assign that Job Queue to a Job: Update job Open the job's edit form → check override on Job Queues and Default Job Queue → select the kubernetes queue → Update (**More on Kubernetes job queues** See [Configure a New Job Queue of Type Kubernetes](../../user-guide/platform-functionality/jobs/kubernetes-job-support.md#configuration) for full details on creating Kubernetes queues and routing jobs to them.)
4. Navigate to **Jobs**, pick a job (e.g. one from `example_app`), and run it.
5. Watch the cluster react:

    ```bash
    kubectl get all
    ```

    You should see a pod named `nautobot-job-<job_result_uuid>-<suffix>` appear and progress through `Pending` - `ContainerCreating` - `Running` - `Completed`.

6. Inspect what the pod did:

    ```bash
    kubectl logs <pod-name>
    ```

7. Check the **Job Results** page in the Nautobot UI. The result should be marked successful and contain the log output.
