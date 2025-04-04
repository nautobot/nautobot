# Cloud Service Network Assignments

The Cloud service network assignments model in Nautobot represents the many-to-many relationship between a [cloud service](./cloudservice.md) and a [cloud network](./cloudnetwork.md). These relationships cannot be managed directly on the cloud services or cloud networks REST API endpoints and must be created, updated or deleted through the endpoint for this model at `/api/cloud/cloud-service-network-assignments/`.
