# # myproject/redis_factory.py



import threading
import time
from typing import Optional

import redis
from azure.identity import DefaultAzureCredential
from django_redis.pool import ConnectionFactory

from redis_entraid.cred_provider import create_from_default_azure_credential


class AzureEntraTokenConnectionFactory(ConnectionFactory):
    REDIS_SCOPE = "https://redis.azure.com/.default"

    def __init__(self, options):
        super().__init__(options)
        self._provider = create_from_default_azure_credential(scopes=("https://redis.azure.com/.default",))
        # self._credential = DefaultAzureCredential()
        self._access_token: Optional[str] = None
        self._expires_on: float = 0
        self._lock = threading.Lock()

        self._object_id = options.get("OBJECT_ID")
        if not self._object_id:
            raise ValueError("OBJECT_ID must be provided in OPTIONS")

    def _get_access_token(self) -> str:
        with self._lock:
            now = time.time()

            if not self._access_token or now >= (self._expires_on - 60):
                token = self._credential.get_token(self.REDIS_SCOPE)
                self._access_token = token.token
                self._expires_on = token.expires_on

            return self._access_token

    def get_connection_pool(self, params):
        token = self._get_access_token()
        print(f"GOT A TOKEN!!! {token}")
        url = params.pop("url", None)
# Example with managed identity using redis-entraid (for use with non-django-redis redis client):
# provider = create_from_managed_identity()
# redis_client = redis.Redis(host='your-cache.redis.cache.windows.net', port=6380, ssl=True, password=provider.get_credentials()[1], username='<object-id>')
# Note: Integrating this specific client with the `django-redis` backend might require custom client classes or patches as the library does not natively support automatic reauthentication within Django's current setup
        params["username"] = self._object_id
        params["password"] = token
        params["credential_provider"] = 
            # username=REDIS_USER_OBJECT_ID,
            # credential_provider=provider,
        if url:
            return redis.ConnectionPool.from_url(url, **params)
redis.Redis(host='rediss://nb021226.redis.cache.windows.net', port=6380, ssl=True, password=self._provider.get_credentials()[1], username='ec45c4b3-738e-4f54-9e86-6df6fcb09575')
        return redis.ConnectionPool(**params)


# class AzureEntraConnectionFactory(ConnectionFactory):
#     """
#     Finalized ConnectionFactory that cleans up the params
#     before initializing the Redis client.
#     """

#     def connect(self, url):
#         # 1. Convert the URL string into a parameter dictionary
#         params = self.make_connection_params(url)

#         # 2. CRITICAL: Remove 'url' because Redis(**params)
#         # doesn't want the raw string again; it wants the components.
#         params.pop("url", None)

#         # 3. Setup Entra ID Credential Provider
#         credential_provider = create_from_default_azure_credential(scopes=("https://redis.azure.com/.default",))

#         # 4. Inject Entra ID and SSL requirements
#         # We also pull the USERNAME from the connection options
#         params.update(
#             {
#                 "credential_provider": credential_provider,
#                 "ssl": True,
#                 "ssl_cert_reqs": ssl.CERT_REQUIRED,
#                 "username": self.options.get("USERNAME"),
#             }
#         )

#         # 5. Ensure password is gone (Entra uses tokens instead)
#         params.pop("password", None)

#         # 6. Initialize the client
#         return Redis(**params)


# import logging

# from django_redis.pool import ConnectionFactory

# logger = logging.getLogger(__name__)
# import redis
# from django.conf import settings
# from redis_entraid.cred_provider import create_from_default_azure_credential


# class CustomConnectionFactory(ConnectionFactory):
#     def __init__(self, options):
#         print("WHOWOHWOHWOW INIT")
#         # allow overriding the default SentinelConnectionPool class
#         options.setdefault(
#             "CONNECTION_POOL_CLASS",
#             # "redis.sentinel.SentinelConnectionPool",
#         )
#         super().__init__(options)

#         # sentinels = options.get("SENTINELS")
#         # if not sentinels:
#         #     error_message = "SENTINELS must be provided as a list of (host, port)."
#         #     raise ImproperlyConfigured(error_message)

#         # provide the connection pool kwargs to the sentinel in case it
#         # needs to use the socket options for the sentinels themselves
#         connection_kwargs = self.make_connection_params(None)
#         connection_kwargs.pop("url")
#         connection_kwargs.update(self.pool_cls_kwargs)

#     def make_connection_params(self, url):
#         """
#         Given a main connection parameters, build a complete
#         dict of connection parameters.
#         """
#         print("IN MAKE CONNECTION PARAMS")
#         kwargs = {
#             "url": url,
#             "parser_class": self.get_parser_cls(),
#         }

#         password = self.options.get("PASSWORD", None)
#         if password:
#             kwargs["password"] = password

#         # socket_timeout = self.options.get("SOCKET_TIMEOUT", None)
#         # if socket_timeout:
#         #     if not isinstance(socket_timeout, (int, float)):
#         #         error_message = "Socket timeout should be float or integer"
#         #         raise ImproperlyConfigured(error_message)
#         #     kwargs["socket_timeout"] = socket_timeout

#         # socket_connect_timeout = self.options.get("SOCKET_CONNECT_TIMEOUT", None)
#         # if socket_connect_timeout:
#         #     if not isinstance(socket_connect_timeout, (int, float)):
#         #         error_message = "Socket connect timeout should be float or integer"
#         #         raise ImproperlyConfigured(error_message)
#         #     kwargs["socket_connect_timeout"] = socket_connect_timeout
#         credential_provider = create_from_default_azure_credential(scopes=("https://redis.azure.com/.default",))
#         # connection_kwargs = self.connection_kwargs
#         connection_kwargs = {}
#         # credential = DefaultAzureCredential()
#         # token = credential.get_token("https://redis.azure.com/.default")
#         # print(f"TOKEN       {token}")
#         # kwargs["password"] = token.token
#         # self.password = token.token
#         connection_kwargs["credential_provider"] = credential_provider
#         return connection_kwargs

#     def make_connection(self, location, options):
#         # Custom logic before creating a connection, e.g., logging
#         print("IN MAKE CONNECTION")
#         # super().make_connection(location, options)

#     #     logger.info(f"Creating a custom Redis connection to {location}")
#     #     # Modify options or location here if needed

#     #     # Call the parent method to create the actual connection
#     #     connection = super().make_connection(location, options)

#     #     # Custom logic after connection is made
#     #     # e.g., setting up specific client-side tracing or authentication
#     #     credential = DefaultAzureCredential()
#     #     token = credential.get_token("https://redis.azure.com/.default")
#     #     self.password = token.token
#     #     return connection

#     # You can also override the get_connection method if needed


# # # This returns an instance of a provider already configured for Azure
# # credential_provider = create_from_default_azure_credential(scopes=("https://redis.azure.com/.default",))


# # # class AzureManagedIdentityConnection(SSLConnection):
# # #     def __init__(self, *args, **kwargs):
# # #         # Force the SSL requirement internally
# # #         kwargs['ssl_cert_reqs'] = ssl.CERT_NONE  # Or ssl.CERT_REQUIRED
# # #         super().__init__(*args, **kwargs)
# # #     def on_connect(self):
# # #         # Your token logic remains the same
# # #         credential = DefaultAzureCredential()
# # #         token = credential.get_token("https://redis.azure.com/.default")
# # #         self.password = token.token
# # #         super().on_connect()

# # # class AzureManagedIdentityConnection(SSLConnection):
# # #     def __init__(self, *args, **kwargs):
# # #         # 1. Inject the SSL requirement directly into the instance
# # #         # This ensures the 'rediss://' handshake doesn't fail
# # #         # even if it's not in the settings.py file.
# # #         kwargs["ssl_cert_reqs"] = ssl.CERT_NONE
# # #         super().__init__(*args, **kwargs)
# # #     def on_connect(self):
# # #         """
# # #         This method is called by redis-py immediately after the
# # #         TCP/SSL socket is established but before the first command.
# # #         """
# # #         # 2. Fetch the fresh Entra ID token
# # #         credential = DefaultAzureCredential()
# # #         token = credential.get_token("https://redis.azure.com/.default")
# # #         # 3. Use the token as the password for the AUTH command
# # #         self.password = token.token
# # #         # 4. Continue with the standard Redis authentication flow
# # #         super().on_connect()


# # # from redis_entraid import CredentialProvider
# # # logger = logging.getLogger(__name__)
# # # class AzureManagedIdentityConnection(SSLConnection):
# # #     def on_connect(self):
# # #         logger.error("!!! CLOUD-INIT: Fetching Azure Token !!!")  # Use error level to bypass filter
# # #         try:
# # #             credential = DefaultAzureCredential()
# # #             token = credential.get_token("https://redis.azure.com/.default")
# # #             self.password = token.token
# # #             super().on_connect()
# # #             logger.error("!!! CLOUD-INIT: Connection Authenticated !!!")
# # #         except Exception as e:
# # #             logger.error(f"!!! CLOUD-INIT: Token Fetch Failed: {e} !!!")
# # #             raise
# # # class EntraIdRedis(Redis):
# # #     def __init__(self, *args, **kwargs):
# # #         print("IN ENTRAID")
# # #         print(dir(self))
# # #         # print(self.get_connection_kwargs())
# # #         # print(vars(self))
# # #         # print(kwargs["connection_pool"])
# # #         # self.connection_pool
# # #         # Create credential provider for Azure Cache for Redis
# # #         self.credential_provider = create_from_default_azure_credential(("https://redis.azure.com/.default",))
# # #         print("DEBUGGING: Creating Redis connection with Azure Entra ID authentication...")
# # #         # print(kwargs)
# # #         # print(dir(kwargs["connection_pool"].connection_kwargs))
# # #         # print(kwargs["connection_pool"].connection_kwargs)
# # #         # print(dir(self.credential_provider))
# # #         # self.credential_provider.get_credentials()
# # #         # credential = DefaultAzureCredential()
# # #         # token = credential.get_token("https://redis.azure.com/.default")
# # #         # # 2. Set the credentials for this specific connection instance
# # #         # # 'self.username' should be the Object ID of your Managed Identity
# # #         # self.password = token.token
# # #         # # Create a copy of connection kwargs and inject the credential provider
# # #         # print(kwargs["connection_pool"].connection_class)
# # #         # connection_kwargs = kwargs["connection_pool"].connection_kwargs
# # #         # kwargs["connection_pool"].connection_kwargs = self.connection_kwargs
# # #         # Remove password-based authentication if present
# # #         # connection_kwargs.pop("password", None)
# # #         # connection_kwargs.pop("username", None)
# # #         # Inject the credential provider
# # #         # connection_kwargs["credential_provider"] = credential_provider
# # #         # print(f"Connection kwargs for Redis: {list(connection_kwargs.keys())}")
# # #         # print(f"Connection class: {self.connection_class.__name__}")
# # #         # print(kwargs["connection_pool"].get_connection)
# # #         # Username is the Client ID (User-Assigned) or Object ID (System-Assigned)
# # #         # self.username = username
# # #         # self.credential = DefaultAzureCredential()
# # #         # print(dir(kwargs["connection_pool"]))
# # #         # print(kwargs["connection_pool"])
# # #         # kwargs["connection_class"] = AzureManagedIdentityConnection()
# # #         # kwargs["credential_provider"] = create_from_default_azure_credential(DefaultAzureCredential())
# # #         # kwargs["ssl"] = True
# # #         # kwargs["connection_pool"].connection_class["ssl_cert_reqs"] = ssl.CERT_NONE
# # #         # print(dir(kwargs["connection_pool"].connection_class))
# # #         # print(dir(kwargs["connection_pool"]))
# # #         # print(vars(kwargs["connection_pool"]))
# # #         # kwargs["connection_pool"]["ssl_certs_reqs"] = ssl.CERT_NONE
# # #         # kwargs["ssl_cert_reqs"] = ssl.CERT_NONE
# # #         super().__init__(*args, **kwargs)
# # # class AzureRedisCredentialProvider(redis.CredentialProvider):
# # #     def __init__(self, username):
# # #         # Username is the Client ID (User-Assigned) or Object ID (System-Assigned)
# # #         self.username = username
# # #         self.credential = DefaultAzureCredential()
# # #     def get_credentials(self):
# # #         """Called by redis-py whenever a new connection needs to AUTH."""
# # #         token = self.credential.get_token("https://redis.azure.com/.default")
# # #         return self.username, token.token
# # # # class AzureRedisConnectionFactory(ConnectionFactory):
# # # #     def __init__(self):
# # # #         print("INIT")
# # # #         super().__init(self)
# # # #     def get_connection_kwargs(self, *args, **kwargs):
# # # #         # 1. Start with the default arguments from the URL
# # # #         conn_kwargs = super().get_connection_kwargs(*args, **kwargs)
# # # #         # 2. Fetch a fresh Managed Identity token
# # # #         # This will be called whenever a new connection pool is created
# # # #         credential = DefaultAzureCredential()
# # # #         token = credential.get_token("https://redis.azure.com/.default")
# # # #         # 3. Inject the mandatory Azure RBAC credentials
# # # #         conn_kwargs.update(
# # # #             {
# # # #                 "password": token.token,
# # # #                 "connection_class": SSLConnection,
# # # #                 "ssl_cert_reqs": ssl.CERT_NONE,  # Required for Azure handshakes
# # # #             }
# # # #         )
# # # #         return conn_kwargs
# # # import logging
# # # from redis.connection import Connection
# # # logger = logging.getLogger(__name__)
# # # class AzureManagedIdentityConnection(Connection):
# # #     def on_connect(self):
# # #         """
# # #         Invoked immediately after the socket is established.
# # #         We inject the fresh Managed Identity token here.
# # #         """
# # #         try:
# # #             # 1. Fetch a fresh token from Azure
# # #             # The scope for Azure Redis is always this specific URL
# # #             credential = DefaultAzureCredential()
# # #             token_obj = credential.get_token("https://redis.azure.com/.default")
# # #             # 2. Set the password attribute that super().on_connect() will use
# # #             self.username = "ec45c4b3-738e-4f54-9e86-6df6fcb09575"
# # #             self.password = token_obj.token
# # #             logger.info("Successfully acquired fresh Azure Redis token.")
# # #         except Exception as e:
# # #             logger.error(f"Failed to acquire Azure Managed Identity token: {e}")
# # #             raise
# # #         # 3. Call the parent on_connect, which sends the AUTH command to Redis
# # #         super().on_connect()
# # # # # Save this in your nautobot_config.py or a custom module
# # # from azure.identity import DefaultAzureCredential
# # # from redis import CredentialProvider
# # # class AzureRedisCredentialProvider(CredentialProvider):
# # #     def __init__(self, username):
# # #         self.username = username
# # #         self.credential = DefaultAzureCredential()
# # #     def get_credentials(self):
# # #         # Fetch fresh token from Managed Identity
# # #         token = self.credential.get_token("https://redis.azure.com/.default")
# # #         # Return tuple of (username, password)
# # #         return self.username, token.token
# # # import redis
# # # class AzureManagedIdentityConnection(redis.Connection):
# # #     """
# # #     Redis connection class that authenticates to Azure Cache for Redis using a Managed Identity token.
# # #     This class fetches a fresh Azure Managed Identity token for each connection and uses it as the password.
# # #     """
# # #     def __init__(self, *args, **kwargs):
# # #         """
# # #         Initialize the AzureManagedIdentityConnection.
# # #         Parameters
# # #         ----------
# # #         *args : tuple
# # #             Positional arguments passed to the base redis.Connection.
# # #         **kwargs : dict
# # #             Keyword arguments passed to the base redis.Connection.
# # #         """
# # #         # Add custom logic here
# # #         print("Using AzureManagedIdentityConnection!")
# # #         self.password = None  # Ensure attribute is defined in __init__
# # #         super().__init__(*args, **kwargs)
# # # def connect(self):
# # #     """
# # #     Establish a connection to Azure Cache for Redis using a Managed Identity token.
# # #     Fetches a fresh token and sets it as the password before connecting.
# # #     """
# # #     # 1. Fetch the Managed Identity token
# # #     # Scope for Azure Cache for Redis is always: https://redis.azure.com/.default
# # #     credential = DefaultAzureCredential()
# # #     token = credential.get_token("https://redis.azure.com/.default")
# # #     # 2. Set the credentials for this specific connection instance
# # #     # 'self.username' should be the Object ID of your Managed Identity
# # #     self.password = token.token
# # #     # 3. Proceed with the standard connection logic
# # #     return super().connect()
# # # def refresh_token(self):
# # #     """
# # #     Refresh the Managed Identity token and update the password attribute.
# # #     """
# # #     credential = DefaultAzureCredential()
# # #     token = credential.get_token("https://redis.azure.com/.default")
# # #     self.password = token.token
# # #     # def _connect(self):
# # #     #     print("IN ON CONNECT CONNECTION CLASS!!!!!!!!!!!!!!!!!!")
# # #     #     # 1. Fetch fresh token
# # #     #     # Using a singleton-like credential object is better for performance
# # #     #     credential = DefaultAzureCredential()
# # #     #     token = credential.get_token("https://redis.azure.com/.default")
# # #     #     # 2. Update the password for this connection instance
# # #     #     self.password = token.token
# # #     #     # 3. Now let the standard redis-py logic send the AUTH command
# # #     #     # super().on_connect()
# # #     # def connect_check_health(self, check_health: bool = False, retry_socket_connect: bool = True):
# # #     #     print("WOAH")
# # from azure.identity import DefaultAzureCredential
# # from redis.credentials import CredentialProvider
# # class ManagedIdentityCredentialProvider(CredentialProvider):
# #     def __init__(self, client_id):
# #         self.client_id = client_id
# #         self.credential = DefaultAzureCredential()
# #     def get_credentials(self):
# #         credential_provider = create_from_default_azure_credential(("https://redis.azure.com/.default",))
# #         # token = self.credential.get_token("https://redis.azure.com/.default").token
# #         return credential_provider.token


# class CustomConnectionPool(redis.ConnectionPool):
#     def __init__(self, *args, **kwargs):
#         # Add custom logic here
#         print("Using CustomConnectionPool!")
#         print(dir(self))
#         # print(self.get_connection)
#         print(kwargs)
#         # print(dir(settings))
#         print(settings.CELERY_BROKER_URL)
#         # print(dir(self))

#         self.credential_provider = create_from_default_azure_credential(("https://redis.azure.com/.default",))
#         # kwargs["connection_class"] = AzureMIConnection
#         super().__init__(*args, **kwargs)
#         # print(self)
#         # print(dir(self))
#         # print(settings)
#         print(settings.CELERY_BROKER_URL)


# # from redis.connection import SSLConnection


# # class AzureMIConnection(SSLConnection):
# #     def __init__(self, *args, **kwargs):
# #         print("using AZUREMICONNECTION")
# #         print(dir(self))
# #         print(kwargs)
# #         kwargs["credential_provider"] = ManagedIdentityCredentialProvider("ec45c4b3-738e-4f54-9e86-6df6fcb09575")
# #         super().__init__(*args, **kwargs)
# #         print(kwargs)

# #     # def on_connect(self):
# #     #     # Your token logic remains the same
# #     #     # credential = DefaultAzureCredential()
# #     #     # token = credential.get_token("https://redis.azure.com/.default")
# #     #     # self.password = token.token
# #     #     super().on_connect()


# # # def make_connection(self):
# # #     """Create a new connection.  Can be overridden by child classes."""
# # #     print("IN MAKE_CONNECTION!!!!!!!!!!!!!!!!!!")
# # #     # 1. Fetch fresh token
# # #     # Using a singleton-like credential object is better for performance
# # #     credential = DefaultAzureCredential()
# # #     token = credential.get_token("https://redis.azure.com/.default")

# # #     # 2. Update the password for this connection instance
# # #     self.password = token.token

# # #     credential_provider = AzureRedisCredentialProvider
# # #     # 3. Now let the standard redis-py logic send the AUTH command
# # #     return super().make_connection()



