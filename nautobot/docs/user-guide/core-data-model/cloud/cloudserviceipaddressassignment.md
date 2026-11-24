# Cloud Service IP Address Assignments

+++ 3.3.0

The Cloud service IP address assignments model in Nautobot represents the many-to-many relationship between a [cloud service](./cloudservice.md) and an [IP address](../ipam/ipaddress.md). These relationships cannot be managed directly on the cloud services or IP addresses REST API endpoints and must be created, updated or deleted through the endpoint for this model at `/api/cloud/cloud-service-ip-address-assignments/`. In the web UI, the IP addresses of a cloud service can be selected in the cloud service edit form.
