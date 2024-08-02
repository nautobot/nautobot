# Cloud

The new Cloud data models allow the modeling of [cloud networks](./cloudnetwork.md) and [cloud services](./cloudservice.md). Here is an example of how these models can be used together to model an AWS Direct Connect.

## Example

### Diagram

![AWS Direct Connect](../../../media/models/cloud_aws_direct_connect_light.png#only-light)
![AWS Direct Connect](../../../media/models/cloud_aws_direct_connect_dark.png#only-dark)

### Pseudocode

```yaml
# Pseudocode
manufacturers:
  - name: "Amazon"

cloud_accounts:
  - name: "AWS"
    account_number: "A-123456"
    provider: "Amazon"

cloud_resource_type:
  - name: "VPC"
    provider: "Amazon"
    content_types:
      - cloud:cloud_network

  - name: "S3"
    provider: "Amazon"
    content_types:
      - cloud:cloud_service

cloud_networks:
  - name: "VPC-01"
    cloud_resource_type: "VPC"
    cloud_account: "AWS"
    prefixes: [<prefix:10.1.0.0/16>]

cloud_services:
  - name: "S3 Bucket 3"
    cloud_resource_type: "S3"
    cloud_networks:
      - "VPC-01"

circuits:
  - name: "AWS Direct Connect 1"
    termination_a:
      site: "Customer Office"
    termination_z:
      cloud_network: "VPC-01"

```

## Entity Relationship Diagram

This schema illustrates the connections between related models.

```mermaid
---
title: Cloud Entity Relationship Diagram
---
erDiagram
    CloudAccount {
        string name UK
        string account_number
        Manufacturer provider FK
        SecretsGroup secrets_group FK
    }

    CloudNetwork {
        string name UK
        string description
        CloudNetwork parent FK
        CloudResourceType cloud_resource_type FK
        CloudAccount cloud_account FK
        Prefix prefixes FK
        CloudService cloud_services FK
        json extra_config
    }

    CloudResourceType {
        string name UK
        Manufacturer provider FK
        json config_schema
        ContentType content_types FK
    }

    CloudService {
        string name UK
        string description
        CloudNetwork cloud_networks FK
        CloudAccount cloud_account FK
        CloudResourceType cloud_resource_type FK
    }

    Manufacturer {
        string name UK
        CloudAccount cloud_accounts FK
        CloudResourceType cloud_resource_types FK
    }

    Prefix {
        VarbinaryIPField network UK
        VarbinaryIPField broadcast
        int prefix_length UK
        Namespace namespace FK
        CloudNetwork cloud_networks FK
    }

    SecretsGroup {
        string name UK
        Secret secrets FK
        CloudAccount cloudaccount_set FK
    }

    CloudAccount ||--o{ Manufacturer : requires
    CloudAccount ||--o{ SecretsGroup : has

    CloudNetwork ||--o{ CloudAccount : requires
    CloudNetwork }o--o{ Prefix : "through CloudNetworkPrefixAssignment"
    CloudNetwork }o--o{ CloudService : "through CloudNetworkServiceAssignment"
    CloudNetwork ||--o{ CloudResourceType : requires
    CloudNetwork ||--o{ CloudNetwork : "contains children"

    CloudResourceType ||--o{ Manufacturer : requires

    CloudService ||--o{ CloudAccount : has
    CloudService ||--o{ CloudResourceType : requires
```
