# OpenTelemetry

+++ 2.2.0

This guide explains how to implement [OpenTelemetry](https://opentelemetry.io).

## Install Requirements

### Install Python OpenTelemetry packages

!!! warning
    This and all remaining steps in this document should all be performed as the `nautobot` user!

    Hint: Use `sudo -iu nautobot`

Activate the Python virtual environment and install the OpenTelemetry packages using pip:

```no-highlight
source /opt/nautobot/bin/activate
pip3 install "nautobot[opentelemetry]"
```

Once installed, add the package to `local_requirements.txt` to ensure it is re-installed during future rebuilds of the virtual environment:

```no-highlight
echo "nautobot[opentelemetry]" >> /opt/nautobot/local_requirements.txt
```

## Configuration

See the [Nautobot OpenTelemetry Guide](../guides/opentelemetry.md) for configuration information.
