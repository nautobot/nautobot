# Using Local Kubernetes Cluster

This guide will help you set up a local Kubernetes cluster using [Kind](https://kind.sigs.k8s.io/) and connect running Nautobot containers to the Kind network.

## Installing Kind

In this chapter we will install Kind on your local machine and create a new Kind Kubernetes cluster.

To install Kind on macOS:

```bash
brew install kind
```

To install Kind on Linux:

```bash
curl -fsSL \
    "https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64" \
    --output /usr/local/bin/kind
chmod +x /usr/local/bin/kind
```

## Creating a Kind Kubernetes Cluster

In this chapter, we will create a new Kind Kubernetes cluster for local development, along with a client configuration file.

!!! Note
    To access the cluster from the Nautobot containers, remember to regenerate the `kubeconfig` file as described in the second step of this chapter.

To create a new Kind cluster:

```bash
kind create cluster \
    --name=nautobot \
    --config=development/kind-config.yaml \
    --kubeconfig=./development/kind-kube-config
```

Expected output shows the cluster is created:

```text
Creating cluster "nautobot" ...
 ✓ Ensuring node image (kindest/node:v1.31.0) 🖼
 ✓ Preparing nodes 📦
 ✓ Writing configuration 📜
 ✓ Starting control-plane 🕹️
 ✓ Installing CNI 🔌
 ✓ Installing StorageClass 💾
Set kubectl context to "kind-nautobot"
You can now use your cluster with:

kubectl cluster-info --context kind-nautobot

Have a question, bug, or feature request? Let us know! https://kind.sigs.k8s.io/#community 🙂
```

To regenerate the `kubeconfig` file with an internal cluster IP address for access from connected Nautobot containers, run the following command:

```bash
kind get kubeconfig \
    --internal \
    --name=nautobot \
    > ./development/kind-kube-config
```

## Connecting Nautobot Containers

This chapter will help you connect running Nautobot containers to the Kind network.

!!! Note
    These steps needs to be done every time you start the Nautobot containers.

Verify Nautobot containers are running:

```bash
# Start Nautobot containers if they are not running
invoke start

# Verify the containers are running
docker ps
```

!!! Info
    In this example, we are connecting the `nautobot` and `celery_worker` containers to the Kind network to allow access to the Kind cluster from these containers during development. Connecting the `celery_worker` container is necessary if you want to run Nautobot Jobs that access the Kind Kubernetes cluster.

You should see `nautobot-nautobot-1` and `nautobot-celery_worker-1` containers running and in a healthy state:

```text
CONTAINER ID   IMAGE                           COMMAND                  CREATED          STATUS          PORTS                    NAMES
...
1f191e104357   local/nautobot-dev:local-py3.11 "watchmedo auto-rest…"   2 minutes ago    Up 37 seconds (healthy)   0.0.0.0:8081->8080/tcp, [::]:8081->8080/tcp nautobot-celery_worker-1
d396ed398a4c   local/nautobot-dev:local-py3.11 "/docker-entrypoint.…"   2 minutes ago    Up 2 minutes (healthy)    0.0.0.0:8080->8080/tcp, :::8080->8080/tcp nautobot-nautobot-1
...
```

Verify the Kind Docker network name is `kind`:

```bash
docker network ls
```

You should see all networks, including the `kind` network.

```text
NETWORK ID     NAME    DRIVER    SCOPE
...
6de64b53be75   kind    bridge    local
...
```

Connect running Nautobot containers to the Kind network:

```bash
docker network connect kind nautobot-nautobot-1
docker network connect kind nautobot-celery_worker-1
```

Now the selected Nautobot containers are connected to the Kind network and can access the Kind Kubernetes cluster.

## Using `kubectl`

To access the Kind Kubernetes cluster from the Nautobot container, you can use `kubectl` CLI tool.

!!! Note
    If you just want to use Python scripts to interact with the cluster, you can skip this chapter. However, it's recommended to install `kubectl` as it is a powerful tool for interacting with the Kubernetes cluster for debugging and testing.

To verify the connection from Nautobot container to the Kind cluster:

```bash
# Open shell in the running Nautobot container
invoke cli

# Install kubectl
apt update
apt install kubernetes-client

# Test the connection
export KUBECONFIG=/source/development/kind-kube-config
kubectl cluster-info
```

You should see the following output:

```text
Kubernetes control plane is running at https://nautobot-control-plane:6443
CoreDNS is running at https://nautobot-control-plane:6443/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.
```

## Running a Test Job

You can verify the connection by creating the testing Kubernetes job:

```bash
invoke cli

export KUBECONFIG=/source/development/kind-kube-config
./development/create_k8s_job.py
```

!!! Note
    For the following steps, the `kubectl` CLI tool must be installed as described in the previous chapter.

To verify the job is running.

```bash
kubectl get job
```

You should see the following output:

```text
NAME       STATUS    COMPLETIONS   DURATION   AGE
demo-job   Running   0/1           6s         6s
```

!!! Info
    The job will run for 10 seconds and then complete.

You can check the logs of the job:

```bash
kubectl logs job/demo-job --follow
```

Expected output:

```text
Hello, Kubernetes!
```

!!! Warning
    You should delete the job after you are done with it, to be able to run the script again.

To delete the job:

```bash
kubectl delete job demo-job
```

## Cleaning Up

To clean up the Kind cluster and the `kubeconfig` file:

```bash
kind delete cluster --name=nautobot
rm development/kind-kube-config
```
