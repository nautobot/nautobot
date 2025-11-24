# Getting Started with Load Balancer Models

## Key Features and Functionality

- **Multi-vendor Support:** Native compatibility with popular load balancing vendors including F5, Citrix NetScaler, A10 Networks, VMware Avi Load Balancer, and Fortinet.
- **CRUD Operations:** Manage Load Balancer resources directly within Nautobot UI, REST API, and GraphQL.
- **Integration and Extensibility:** Leverage Nautobot’s extensibility framework for deeper integration with other applications and automation systems.
- **Configuration Management:** Generate basic load balancing configurations directly from stored data models.

## Quick Walkthrough

!!! info "Looking for a full example?"
    This section walks you through creating each data model step-by-step. If you prefer to start with real-world data and configuration output, check out the [F5 Simple Use Case](#f5-simple-load-balancing-use-case) or the [F5 Advanced Use Case](#f5-advanced-load-balancing-use-case).

### 1. IP Address and Subnet Preparation

- Ensure IP Addresses or Prefixes are already created within Nautobot’s IP Address Management (IPAM) module.
- Virtual Servers require unique IP Addresses (VIPs) sourced from IPAM.
- If you haven't already configured your IPAM, follow these [instructions](getting-started/ipam.md#creating-a-prefix).

### 2. Creating Virtual Servers

- Navigate to the Load Balancer module within Nautobot's UI.
- Define a Virtual Server by assigning it a unique VIP from Nautobot’s IPAM module. Each Virtual Server represents a managed IP endpoint used to distribute incoming traffic to backend Pool Members.
- Select the protocol (TCP, UDP, HTTP, HTTPS, etc.) from available predefined choices.
- Associate the Virtual Server directly with a LoadBalancerPool.

### 3. Configuring Load Balancer Pools

- Set up LoadBalancerPools that can be associated with Virtual Servers.
- Define load balancing algorithms (e.g., round-robin, least connections).
- Optionally associate the pool with a Health Check Monitor to maintain high availability and performance.

### 4. Adding Load Balancer Pool Members

- Populate LoadBalancerPools with Pool Members by specifying individual IP Addresses, port numbers, and optional labels for easy identification.
- Pool Members represent backend servers responsible for processing client requests distributed by the pool.

### 5. Health Check Configuration

- Define Health Checks independently using the HealthCheckMonitor model.
- After creation, associate Health Checks with Pools and/or Pool Members to monitor their operational status, ensuring reliability and automatically disabling unhealthy servers.

### 6. Certificate Profile Configuration

- Certificate Profiles manage SSL/TLS settings, including the paths to certificate files, chain files, and private keys.
- Set certificate expiration dates and proactively manage renewals within Nautobot.
- Attach Certificate Profiles to Virtual Servers to handle secure communications effectively.

## Screenshots Showcasing Load Balancer Data Model

![Virtual Servers List](./images/load-balancer/load-balancer-virtual-server-light.png#only-light){ .on-glb }
![Virtual Servers List](./images/load-balancer/load-balancer-virtual-server-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/virtual-servers/`"

A list view of all configured Virtual Servers, including name, load balancer type, protocol, and associated pools.

![Virtual Server Detail](./images/load-balancer/load_balancer-virtual-server-detail-light.png#only-light){ .on-glb }
![Virtual Server Detail](./images/load-balancer/load-balancer-virtual-server-detail-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/virtual-servers/19736556-378c-4a61-b3b8-aaae2f2f422c/`"

Detailed view of a single Virtual Server, showing the VIP, port, protocol, associated Certificate Profile, and linked Load Balancer Pool.

![Load Balancer Pools List](./images/load-balancer/load-balancer-pools-light.png#only-light){ .on-glb }
![Load Balancer Pools List](./images/load-balancer/load-balancer-pools-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/load-balancer-pools/`"

A list view of Load Balancer Pools, showing pool names and algorithms.

![Load Balancer Pool Detail](./images/load-balancer/load-balancer-pools-detail-light.png#only-light){ .on-glb }
![Load Balancer Pools Detail](./images/load-balancer/load-balancer-pools-detail-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/load-balancer-pools/d5097984-9c43-4c33-a6b2-43339dfd65f4/`"

Detailed view of a specific Load Balancer Pool, including load balancing algorithm, associated pool members, and associated Health Check Monitor.

![Load Balancer Pool Members List](./images/load-balancer/load-balancer-pool-member-light.png#only-light){ .on-glb }
![Load Balancer Pool Members List](./images/load-balancer/load-balancer-pool-member-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/load-balancer-pool-members/`"

A list view of Load Balancer Pool Members, displaying IP Addresses, ports, and status.

![Load Balancer Pool Member Detail](./images/load-balancer/load-balancer-pool-member-detail-light.png#only-light){ .on-glb }
![Load Balancer Pool Member Detail](./images/load-balancer/load-balancer-pool-member-detail-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/load-balancer-pool-members/132759f4-1fa9-47dd-94f3-371abb943dd7/`"

Detailed view of an individual Load Balancer Pool Member, including its linked pool, port, health check monitor configuration, and certificate profile.

![Health Checks List](./images/load-balancer/load-balancer-health-check-light.png#only-light){ .on-glb }
![Health Checks List](./images/load-balancer/load-balancer-health-check-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/health-check-monitors/`"

A list view of a Health Check Monitor showing health check types, port, interval, retry and timeout settings.

![Health Check Detail](./images/load-balancer/load-balancer-health-check-detail-light.png#only-light){ .on-glb }
![Health Check Detail](./images/load-balancer/load-balancer-health-check-detail-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/health-check-monitors/497deb96-e43b-4408-b3fb-2a1ae6bf7856/`"

Detailed view of a Health Check Monitor including interval, timeout, and target port.

![Certificate Profiles List](./images/load-balancer/load-balancer-cert-light.png#only-light){ .on-glb }
![Certificate Profiles List](./images/load-balancer/load-balancer-cert-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/certificate-profiles/`"

A list view of available Certificate Profiles used for SSL/TLS termination, showing certificate type and other optional fields.

![Certificate Profile Detail](./images/load-balancer/load-balancer-cert-detail-light.png#only-light){ .on-glb }
![Certificate Profile Detail](./images/load-balancer/load-balancer-cert-detail-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/certificate-profiles/c80b768a-498d-4111-be42-e9462afe645e/`"

Detailed view for a Certificate Profile, including certificate type, certificate file path, and key file paths.

## F5 Simple Load Balancing Use Case

This document describes a straightforward example of configuring load balancing for an F5 environment. This use case illustrates the creation of basic Virtual Servers, Load Balancer Pools, and Pool Members.

In this example, we configure:

- A single Virtual Server.
- One Load Balancer Pool.
- One Pool Member.

### 1. IPAM Configuration

Ensure the following IP Addresses exist in Nautobot's IPAM:

- **Virtual IP (VIP):** `10.0.0.1`
- **Pool Member IP:** `10.0.0.1`

![F5 Simple IP Addresses](./images/load-balancer/load-balancer-f5-simple-1-light.png#only-light){ .on-glb }
![F5 Simple IP Addresses](./images/load-balancer/load-balancer-f5-simple-1-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/ipam/ip-addresses/`"

### 2. Configuring Load Balancer Pool

- Navigate to **Load Balancer > Pools**.
- Click **Add Load Balancer Pool**.
    - Name: `pool1`
    - Load Balancing Algorithm: `Round Robin`

![F5 Simple Adding Load Balancer Pool](./images/load-balancer/load-balancer-f5-simple-3-light.png#only-light){ .on-glb }
![F5 Simple Adding Load Balancer Pool](./images/load-balancer/load-balancer-f5-simple-3-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/virtual-servers/add/`"

### 3. Adding a Load Balancer Pool Member

- Navigate to **Load Balancer > Pool Members**.
- Click **Add Load Balancer Pool Member**.
    - IP Address: `10.0.0.1`
    - Load Balancer Pool: `pool1`
    - Status: Active
    - Port: `80`

![F5 Simple Adding Load Balancer Pool Member](./images/load-balancer/load-balancer-f5-simple-5-light.png#only-light){ .on-glb }
![F5 Simple Adding Load Balancer Pool Member](./images/load-balancer/load-balancer-f5-simple-5-dark.png#only-dark){ .on-glb }

### 4. Creating the Virtual Server

In the Nautobot UI:

- Navigate to **Load Balancer > Virtual Servers**.
- Click **Add Virtual Server**.
    - Name: `virtual1`
    - IP Address (VIP): `10.0.0.1`
    - Port: `80`
    - Protocol: `TCP`
    - Load Balancer Pool: `pool1`

![F5 Simple Adding Virtual Server](./images/load-balancer/load-balancer-f5-simple-2-light.png#only-light){ .on-glb }
![F5 Simple Adding Virtual Server](./images/load-balancer/load-balancer-f5-simple-2-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/virtual-servers/add/`"

### 5. Validation and Configuration Snippet

Now that you have successfully inputted the data for a basic Load Balancer data model, you can use [GraphQL](graphql.md) to extract the values needed. Here is a sample GraphQL query for our example:

```graphql
{
  virtual_servers(name: "virtual1") {
    name
    port
    protocol
    vip {
      address
    }
    load_balancer_pool {
      name
      load_balancer_pool_members {
        port
        ip_address {
          address
        }
      }
    }
  }
}

```

A sample JSON response for that query would look like:

```json
{
  "data": {
    "virtual_servers": [
      {
        "name": "virtual1",
        "port": 80,
        "protocol": "TCP",
        "vip": {
          "address": "10.0.0.1/32"
        },
        "load_balancer_pool": {
          "name": "pool1",
          "load_balancer_pool_members": [
            {
              "port": 80,
              "ip_address": {
                "address": "10.0.0.1/32"
              }
            }
          ]
        }
      }
    ]
  }
}
```

![F5 Simple GraphQL](./images/load-balancer/load-balancer-f5-simple-4-light.png#only-light){ .on-glb }
![F5 Simple GraphQL](./images/load-balancer/load-balancer-f5-simple-4-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/graphql/`"

Using that JSON response, you can then build a Jinja2 template following the data model:

```jinja2
{% for virtual_server in data.virtual_servers %}
ltm virtual-address /Common/{{ virtual_server.vip.address.split('/')[0] }} {
    address {{ virtual_server.vip.address.split('/')[0] }}
    arp enabled
    mask 255.255.255.255
    route-advertisement selective
}

ltm virtual /Common/{{ virtual_server.name }} {
    destination /Common/{{ virtual_server.vip.address.split('/')[0] }}:{{ virtual_server.port }}
    ip-protocol {{ virtual_server.protocol | lower }}
    mask 255.255.255.255
    pool /Common/{{ virtual_server.load_balancer_pool.name }}
    source 0.0.0.0/0
    translate-address enabled
    translate-port enabled
}

ltm pool /Common/{{ virtual_server.load_balancer_pool.name }} {
    members {
    {% for member in virtual_server.load_balancer_pool.load_balancer_pool_members %}
        /Common/{{ member.ip_address.address.split('/')[0] }}:{{ member.port }} {
            address {{ member.ip_address.address.split('/')[0] }}
        }
    {% endfor %}
    }
}

{% for member in virtual_server.load_balancer_pool.load_balancer_pool_members %}
ltm node /Common/{{ member.ip_address.address.split('/')[0] }} {
    address {{ member.ip_address.address.split('/')[0] }}
}
{% endfor %}

{% endfor %}
```

Sample output from the template (you can use the Jinja Renderer linked at the bottom of Nautobot):

```no-highlight

ltm virtual-address /Common/10.0.0.1 {
    address 10.0.0.1
    arp enabled
    mask 255.255.255.255
    route-advertisement selective
}

ltm virtual /Common/virtual1 {
    destination /Common/10.0.0.1:80
    ip-protocol tcp
    mask 255.255.255.255
    pool /Common/pool1
    source 0.0.0.0/0
    translate-address enabled
    translate-port enabled
}

ltm pool /Common/pool1 {
    members {
        /Common/10.0.0.1:80 {
            address 10.0.0.1
        }
    }
}


ltm node /Common/10.0.0.1 {
    address 10.0.0.1
}
```

![F5 Simple Jinja2](./images/load-balancer/load-balancer-f5-simple-6-light.png#only-light){ .on-glb }
![F5 Simple Jinja2](./images/load-balancer/load-balancer-f5-simple-6-dark.png#only-dark){ .on-glb }
[//] : # "`https://next.demo.nautobot.com/render-jinja-template/`"

## F5 Advanced Load Balancing Use Case

This use case demonstrates a comprehensive configuration scenario using the Nautobot Load Balancer App for an advanced F5 setup. The example includes multiple pool members, SSL profiles, and detailed health check monitoring.

In this advanced configuration scenario, we illustrate:

- A Virtual Server with multiple Pool Members.
- Advanced Certificate Profile configurations for secure communications.
- Detailed health monitoring via HTTP checks.

### 1. Advanced IPAM Configuration

![F5 Advanced IPAM Configuration](./images/load-balancer/load-balancer-f5-advanced-1-light.png#only-light){ .on-glb }
![F5 Advanced IPAM Configuration](./images/load-balancer/load-balancer-f5-advanced-1-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/ipam/ip-addresses/`"

Ensure these IP Addresses are available in Nautobot's IPAM:

- **Virtual IP (VIP):** `10.0.20.1`
- **Pool Member IPs:** `10.0.20.2`, `10.0.20.3`, `10.0.20.4`

### 2. Health Check Configuration

![F5 Advanced Health Check](./images/load-balancer/load-balancer-f5-advanced-2-light.png#only-light){ .on-glb }
![F5 Advanced Health Check](./images/load-balancer/load-balancer-f5-advanced-2-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/health-check-monitors/add/`"

Before configuring your pools, set up your health checks:

- Navigate to **Load Balancer > Health Check Monitors**.
- Click **Add Health Check Monitor**.
    - Name: `http`
    - Health check type: `HTTP`
    - Port: `80`
    - Interval: `30`
    - Timeout: `5`
    - Retry attempts: `3`

### 3. Certificate Profile Configuration

![F5 Advanced Certificate Profile](./images/load-balancer/load-balancer-f5-advanced-3-light.png#only-light){ .on-glb }
![F5 Advanced Certificate Profile](./images/load-balancer/load-balancer-f5-advanced-3-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/certificate-profiles/add/`"

Define Certificate Profiles:

- Navigate to **Load Balancer > Certificate Profiles**.
- Click **Add Certificate Profile**.
    - Name: `clientssl-fedcheck.app-strong`
    - Certificate Type: `Server`
    - Certificate file path: `fedcheck.app.crt`
    - Chain file path: `fedcheck.app-chain.crt`
    - Key file path: `fedcheck.app.key`

### 4. Configuring Load Balancer Pool

![F5 Advanced Pool Config](./images/load-balancer/load-balancer-f5-advanced-4-light.png#only-light){ .on-glb }
![F5 Advanced Pool Config](./images/load-balancer/load-balancer-f5-advanced-4-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/load-balancer-pools/add/`"

- Navigate to **Load Balancer > Pools**.
- Click **Add Load Balancer Pool**.
    - Name: `pool_live_ident_admin_web_http`
    - Load Balancing Algorithm: Select `Round Robin`
    - Health Check Monitor: Select `http`

### 5. Adding Load Balancer Pool Members

![F5 Advanced Pool Members](./images/load-balancer/load-balancer-f5-advanced-5-light.png#only-light){ .on-glb }
![F5 Advanced Pool Members](./images/load-balancer/load-balancer-f5-advanced-5-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/load-balancer-pool-members/add/`"

- Navigate to **Load Balancer > Pool Members**.
- Add each pool member individually:
    - IP Addresses:
        - `10.0.10.2`
        - `10.0.10.3`
        - `10.0.10.4`
    - Load Balancer Pool: `pool_live_ident_admin_web_http`
    - Status: `Active`
    - Port: `9280`
    - Health Check Monitor: `http`
    - Certificate Profile: `clientssl-fedcheck.app-strong`

### 6. Creating the Virtual Server

![F5 Advanced Virtual Server](./images/load-balancer/load-balancer-f5-advanced-6-light.png#only-light){ .on-glb }
![F5 Advanced Virtual Server](./images/load-balancer/load-balancer-f5-advanced-6-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/load-balancers/virtual-servers/add/`"

- Navigate to **Load Balancer > Virtual Servers**.
- Click **Add Virtual Server**.
    - Name: `vs_live_ident_admin_web_https`
    - IP Address (VIP): `10.0.20.1`
    - Protocol: `TCP`
    - Load Balancer Type: `Layer 7`
    - Port: `443`
    - Load Balancer Pool: `pool_live_ident_admin_web_http`
    - Health Check Monitor: `http`
    - Certificate Profile: `clientssl-fedcheck.app-strong`

### 7. Validation and Configuration Snippet

```graphql
{
  virtual_servers(name: "vs_live_ident_admin_web_https") {
    name
    port
    protocol
    vip {
      address
    }
    certificate_profiles {
      name
      certificate_file_path
      key_file_path
      cipher
    }
    load_balancer_pool {
      name
      health_check_monitor {
        name
        health_check_type
        port
        interval
        timeout
        retry
      }
      load_balancer_pool_members {
        port
        ip_address {
          address
        }
      }
    }
  }
}
```

![F5 Advanced GraphQL Response](./images/load-balancer/load-balancer-f5-advanced-7-light.png#only-light){ .on-glb }
![F5 Advanced GraphQL Response](./images/load-balancer/load-balancer-f5-advanced-7-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/graphql/`"

```json
{
  "data": {
    "virtual_servers": [
      {
        "name": "vs_live_ident_admin_web_https",
        "port": 443,
        "protocol": "TCP",
        "vip": {
          "address": "10.0.20.1/32"
        },
        "certificate_profiles": [
          {
            "name": "clientssl-fedcheck.app-strong",
            "certificate_file_path": "fedcheck.app.crt",
            "key_file_path": "fedcheck.app.key",
            "cipher": ""
          }
        ],
        "load_balancer_pool": {
          "name": "pool_live_ident_admin_web_http",
          "health_check_monitor": {
            "name": "http",
            "health_check_type": "HTTP",
            "port": 80,
            "interval": 30,
            "timeout": 5,
            "retry": 3
          },
          "load_balancer_pool_members": [
            {
              "port": 9280,
              "ip_address": {
                "address": "10.0.20.2/32"
              }
            },
            {
              "port": 9280,
              "ip_address": {
                "address": "10.0.20.3/32"
              }
            },
            {
              "port": 9280,
              "ip_address": {
                "address": "10.0.20.4/32"
              }
            }
          ]
        }
      }
    ]
  }
}
```

![F5 Advanced Jinja2 Template](./images/load-balancer/load-balancer-f5-advanced-8-light.png#only-light){ .on-glb }
![F5 Advanced Jinja2 Template](./images/load-balancer/load-balancer-f5-advanced-8-dark.png#only-dark){ .on-glb }
[//] : # "`https://next.demo.nautobot.com/render-jinja-template/`"

```jinja2
{% for virtual_server in data.virtual_servers %}

ltm virtual-address /Common/{{ virtual_server.vip.address.split('/')[0] }} {
    address {{ virtual_server.vip.address.split('/')[0] }}
    arp enabled
    mask 255.255.255.255
    route-advertisement selective
}

ltm profile client-ssl /Common/{{ virtual_server.certificate_profiles[0].name }} {
    app-service none
    cert-key-chain {
        default {
            cert {{ virtual_server.certificate_profiles[0].certificate_file_path }}
            key {{ virtual_server.certificate_profiles[0].key_file_path }}
        }
    }
    ciphers {{ virtual_server.certificate_profiles[0].cipher or "DEFAULT" }}
    defaults-from /Common/clientssl
}

ltm virtual /Common/{{ virtual_server.name }} {
    destination /Common/{{ virtual_server.vip.address.split('/')[0] }}:{{ virtual_server.port }}
    ip-protocol {{ virtual_server.protocol | lower }}
    mask 255.255.255.255
    pool /Common/{{ virtual_server.load_balancer_pool.name }}
    profiles {
        /Common/{{ virtual_server.certificate_profiles[0].name }} { context clientside }
        /Common/http { }
        /Common/tcp { }
    }
    source 0.0.0.0/0
    source-address-translation { type automap }
    translate-address enabled
    translate-port enabled
    vlans-enabled
}

ltm pool /Common/{{ virtual_server.load_balancer_pool.name }} {
    members {
    {% for member in virtual_server.load_balancer_pool.load_balancer_pool_members %}
        /Common/{{ member.ip_address.address.split('/')[0] }}:{{ member.port }} {
            address {{ member.ip_address.address.split('/')[0] }}
        }
    {% endfor %}
    }
    monitor /Common/{{ virtual_server.load_balancer_pool.health_check_monitor.name }}
}

{% for member in virtual_server.load_balancer_pool.load_balancer_pool_members %}
ltm node /Common/{{ member.ip_address.address.split('/')[0] }} {
    address {{ member.ip_address.address.split('/')[0] }}
}
{% endfor %}

{% endfor %}
```

### Sample output from the template

You can use the Jinja Renderer at the bottom of Nautobot with your JSON output and the sample Jinja2 template:

```no-highlight
ltm virtual-address /Common/10.0.20.1 {
    address 10.0.20.1
    arp enabled
    mask 255.255.255.255
    route-advertisement selective
}

ltm profile client-ssl /Common/clientssl-fedcheck.app-strong {
    app-service none
    cert-key-chain {
        default {
            cert fedcheck.app.crt
            key fedcheck.app.key
        }
    }
    ciphers DEFAULT
    defaults-from /Common/clientssl
}

ltm virtual /Common/vs_live_ident_admin_web_https {
    destination /Common/10.0.20.1:443
    ip-protocol tcp
    mask 255.255.255.255
    pool /Common/pool_live_ident_admin_web_http
    profiles {
        /Common/clientssl-fedcheck.app-strong { context clientside }
        /Common/http { }
        /Common/tcp { }
    }
    source 0.0.0.0/0
    source-address-translation { type automap }
    translate-address enabled
    translate-port enabled
    vlans-enabled
}

ltm pool /Common/pool_live_ident_admin_web_http {
    members {
        /Common/10.0.20.2:9280 {
            address 10.0.20.2
        }
        /Common/10.0.20.3:9280 {
            address 10.0.20.3
        }
        /Common/10.0.20.4:9280 {
            address 10.0.20.4
        }
    }
    monitor /Common/http
}


ltm node /Common/10.0.20.2 {
    address 10.0.20.2
}

ltm node /Common/10.0.20.3 {
    address 10.0.20.3
}

ltm node /Common/10.0.20.4 {
    address 10.0.20.4
}
```

## Representing Vendor-Specific F5 Configuration

This example focuses on core F5 elements that are modeled directly using the Load Balancer data model:

- Certificate Profiles for SSL termination
- Health Check Monitors for backend availability
- Load Balancer Pools and Load Balancer Pool Members
- Virtual Servers using VIPs and ports
- Basic SNAT behavior using template logic (`automap` in the rendered output)

These components are configured directly in Nautobot and shown in the step-by-step configuration and Jinja2 output above.

---

In real-world F5 deployments, additional platform-specific features are often needed but are **not part of the core data model**. These include:

- iRules (e.g., header rewrites, redirects)
- Persistence profiles (e.g., source-IP, cookie)
- HTTP or SSL profile references
- Advanced SNAT configuration
- Routing or rewrite policies

To capture these, you can define **Custom Fields** in Nautobot on models like `VirtualServer` or `LoadBalancerPoolMember`. Depending on the use case:

- Use a **multi-select Custom Field** when users need to choose from a list of known options (e.g., iRule names or profile types).
- Use a **JSON Custom Field** to store structured vendor-specific configuration, such as SNAT policies or fallback persistence logic.

Both field types and many more types are defined are defined through Nautobot’s Custom Field system and will appear in the UI, API, and Jinja2 templates. This provides a flexible, vendor-specific extension mechanism without altering the core data model.

## Sample Citrix NetScaler Jinja Template

This simple template for Citrix NetScaler will work with the same data as above.

```jinja2
{% for virtual_server in data.virtual_servers %}

add ns ip {{ virtual_server.vip.address.split('/')[0] }} 255.255.255.255 -type VIP

{%- if virtual_server.certificate_profiles %}
add ssl certKey {{ virtual_server.certificate_profiles[0].name }} -cert {{ virtual_server.certificate_profiles[0].certificate_file_path }} -key {{ virtual_server.certificate_profiles[0].key_file_path }}
{% endif %}

{%- for member in virtual_server.load_balancer_pool.load_balancer_pool_members %}
add service svc_{{ virtual_server.load_balancer_pool.name }}_{{ loop.index }} {{ member.ip_address.address.split('/')[0] }} {{ virtual_server.protocol | upper }} {{ member.port }}
{%- endfor %}

add servicegroup sg_{{ virtual_server.load_balancer_pool.name }} {{ virtual_server.protocol | upper }}
{% for member in virtual_server.load_balancer_pool.load_balancer_pool_members %}
bind servicegroup sg_{{ virtual_server.load_balancer_pool.name }} svc_{{ virtual_server.load_balancer_pool.name }}_{{ loop.index }}
{%- endfor %}

add lb vserver {{ virtual_server.name }} {{ virtual_server.protocol | upper }} {{ virtual_server.vip.address.split('/')[0] }} {{ virtual_server.port }}
bind lb vserver {{ virtual_server.name }} -serviceGroupName sg_{{ virtual_server.load_balancer_pool.name }}

{% if virtual_server.certificate_profiles %}
bind ssl vserver {{ virtual_server.name }} -certkeyName {{ virtual_server.certificate_profiles[0].name }}
{%- endif %}

{% endfor %}
```

## Sample A10 Networks Jinja Template

This simple template for A10 Networks will work with the same data as above.

```jinja2
{% for virtual_server in data.virtual_servers %}

{% for member in virtual_server.load_balancer_pool.load_balancer_pool_members %}
slb server realserver{{ loop.index }} {{ member.ip_address.address.split('/')[0] }}
  port {{ member.port }} tcp

{%- endfor %}

slb service-group {{ virtual_server.load_balancer_pool.name }} tcp
{%- for member in virtual_server.load_balancer_pool.load_balancer_pool_members %}
  member realserver{{ loop.index }} {{ member.port }}

{%- endfor %}

slb virtual-server {{ virtual_server.name }} {{ virtual_server.vip.address.split('/')[0] }}
  port {{ virtual_server.port }} {{ virtual_server.protocol | lower }}
  service-group {{ virtual_server.load_balancer_pool.name }}
{% if virtual_server.source_nat_pool is defined %}
  source-nat pool {{ virtual_server.source_nat_pool }}
{% endif %}

{% endfor %}
```
