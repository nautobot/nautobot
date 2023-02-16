# Nautobot v2 UI Prototype

## Running it

Install and compile dependencies (note that you'll only use `--npm-install` on initial setup):

```no-highlight
nautobot-server build --npm-install
```

Set the `NAUTOBOT_API_TOKEN` prior to starting the server:

```no-highlight
export NAUTOBOT_API_TOKEN=nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn
```

Start Nautobot on port `8080/tcp`:

```no-highlight
nautobot-server runserver 0.0.0.0:8080 --insecure
```
