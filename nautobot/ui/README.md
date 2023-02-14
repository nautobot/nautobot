# Nautobot v2 UI Prototype

## Running it

Install and compile dependencies:

```no-highlight
nautobot-server build
```

Configure Nautobot to pass through authentication over CORS by putting this into your `nautobot_config.py`:

```python
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
SESSION_COOKIE_SAMESITE = None
```

Set the `NAUTOBOT_API_TOKEN` prior to starting Node.js:

```no-highlight
export NAUTOBOT_API_TOKEN=nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn
```

Start Nautobot on port `8888/tcp`:

```no-highlight
nautobot-server runserver 0.0.0.0:8888 --insecure
```
