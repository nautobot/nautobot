#!/usr/bin/env python
"""Demonstrates how to create a Kubernetes Job using the Python client library."""

from kubernetes import client, config
from kubernetes.client.rest import ApiException

config.load_kube_config()


def create_job_object():
    container = client.V1Container(
        name="demo-job-container", image="busybox", command=["/bin/sh", "-c", "echo Hello, Kubernetes! && sleep 10"]
    )
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": "demo-job"}),
        spec=client.V1PodSpec(restart_policy="Never", containers=[container]),
    )
    job_spec = client.V1JobSpec(template=template, backoff_limit=4)
    job = client.V1Job(api_version="batch/v1", kind="Job", metadata=client.V1ObjectMeta(name="demo-job"), spec=job_spec)
    return job


def create_job(api_instance, job):
    try:
        api_response = api_instance.create_namespaced_job(body=job, namespace="default")
        print(f"Job created. Status={api_response.status}")
    except ApiException as exc:
        print(f"Exception when creating job: {exc}")


def main():
    batch_v1 = client.BatchV1Api()
    job = create_job_object()
    create_job(batch_v1, job)


if __name__ == "__main__":
    main()
