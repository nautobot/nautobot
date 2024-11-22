# Kubernetes Job

## When to Use Kubernetes Jobs

## How to Use Kubernetes Jobs

Consult the documentation from the offical [kubernetes page](https://kubernetes.io/docs/home/) and learn how to set up a simple kubernetes cluster with pods running Nautobot containers in your own development environment from this [doc](../../../development/core/kubernetes-job-support.md).

Once you have the correct environment setup, executing kubernetes job would just be as simple as assigning a [job queue](../jobs/jobqueue.md) with type kubernetes and running the job on it. Below is a detail guide on how you can do that in Nautobot.

### Configure a New Job Queue of Type Kubernetes

Go to the Navigation bar on your left hand side and look at the Jobs Section. You should see Job Queues at the very end of the section. Click on the plus button next to the Job Queues entry and this will take us to a form for creating a new job queue.
[Insert Image here]
We can give the name "kubernetes" to the new job queue and select "Kubernetes" from the Queue Type dropdown.
[Insert Image here]
Scroll down and click on the create button. A new Job Queue with name "kubernetes" and with type Kubernetes should be created.
[Insert Image here]

### Assign that Job Queue to a Job

Go to a Job and assign the newly created kubernetes job queue to the job. We will be using the "Export Object List" system job here.
[Insert Image here]
Check the override default value checkbox on the `Job Queues` field and select the kubernetes job queue from the dropdown.
[Insert Image here]
Check the override default value checkbox on the `Default Job Queue` field and select the kubernetes job queue from the dropdown.
[Insert Image here]
Click on the update button when we are finished.

### Run the Job

After clicking on the update button after the previous step, we should be redirected to the table of jobs. Click on the link that says "Export Object List". This should take us to the Job Run Form.
[Insert Image here]
Select an option for the Content Type field dropdown and notice that the Job queue is already filled out with the kubernetes job queue that we assigned to this job from previous steps. So we do not need to make any changes there.
[Insert Image here]
Click on the "Run Job Now" button and we should be directed to the job result page.

### Inspect the Job Result

You can inspect the job result and the job logs in this page. Notice the two job log entries that reads something like "Creating job pod (pod-name) in namespace default" and Reading job pod (pod-name) in namespace default". Those entries indicate that a Kubernetes Job pod was executing the job for us.

[Insert Image here]

## Running a Job with Celery in Kubernetes

Running nautobot jobs with Celery and Celery workers within a Kubernetes Cluster has several potential downsides. To list a few:

1. Resource Allocation Issues: Celery workers require resource allocation (CPU/Memory). Although Kubernetes allows for limits and requests, under-allocation of resources can cause crashes, while over-allocation can be quite wasteful
2. In some enviroments with resource contention, Kubernetes may evict pods with celery workers, leading to task loss or interruptions.
3. If a celery worker pod crashes or is terminated, any in-progress tasks without any retry mechanisms can be lost and their results untraceable.

## High Level Flow of Kubernetes Components

## How to Configure Environment Variables
