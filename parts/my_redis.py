# import logging
# from typing import Optional


from django_redis.client import DefaultClient

# from health_check.base import HealthCheck
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceUnavailable

# from redis import Redis
# from redis.exceptions import ConnectionError as RedisConnectionError
# from redis_entraid.cred_provider import EntraIdCredentialsProvider, create_from_default_azure_credential

# logger = logging.getLogger(__name__)


class MyTestRedisClient(DefaultClient):
    def __init__(self, server, params, backend):
        print(self)
        print(server)
        print(params)
        print(backend)
        super().__init__(server, params, backend)


from health_check.plugins import plugin_dir


class MyHealthCheck(BaseHealthCheckBackend):
    def check_status(self):
        print("in check_status")
        try:
            1 / 0
        except Exception as e:
            self.add_error(ServiceUnavailable("Unknown error"), e)


plugin_dir.register(MyHealthCheck)

# class AzureRedisClient(DefaultClient):
#     """
#     Custom Redis client that uses Azure Entra ID (formerly Azure AD) authentication
#     via Managed Identity instead of password-based authentication.

#     This client extends django-redis's DefaultClient and overrides the connect method
#     to inject Azure Managed Identity credentials through the credential provider pattern.

#     Usage in Django settings:

#     CACHES = {
#         "default": {
#             "BACKEND": "django_redis.cache.RedisCache",
#             "LOCATION": "rediss://your-redis.redis.cache.windows.net:6380",
#             "OPTIONS": {
#                 "CLIENT_CLASS": "paas_auth.cache.backends.redis.AzureRedisClient",
#                 "CONNECTION_POOL_KWARGS": {
#                     "ssl": True,
#                     "decode_responses": True,
#                 },
#             },
#         }
#     }
#     """

#     def __init__(self, server, params, backend):
#         """
#         Initialize the Azure Redis client.

#         Args:
#             server: Redis server connection string(s)
#             params: Cache configuration parameters
#             backend: The Django cache backend instance
#         """
#         super().__init__(server, params, backend)
#         self._credential_provider: Optional[EntraIdCredentialsProvider] = None
#         logger.info("AzureRedisClient initialized with Managed Identity authentication")

#     def _get_credential_provider(self) -> EntraIdCredentialsProvider:
#         """
#         Use Azure Workload Identity to get an AAD token for Azure Cache for Redis.
#         Token lifetime is typically 1 hour; we'll cache it and refresh when needed.
#         """
#         credential_provider = create_from_default_azure_credential(
#             ("https://redis.azure.com/.default",),
#         )
#         return credential_provider

#     def connect(self, index: int = 0) -> Redis:
#         """
#         Override connect to create a Redis connection with Azure Managed Identity authentication.

#         Instead of using password authentication, this method injects an Azure Entra ID
#         credential provider that automatically handles token acquisition and refresh.

#         Args:
#             index: Connection index for replication setups (default: 0)

#         Returns:
#             Redis: Connected Redis client instance

#         Raises:
#             RedisConnectionError: If connection fails
#         """
#         try:
#             # Get the credential provider
#             credential_provider = self._get_credential_provider()
#             print(credential_provider.get_credentials())
#             # Get the server connection string for this index
#             server_url = self._server[index]
#             logger.info(f"Connecting to Redis server: {server_url}")

#             # Parse connection parameters from the server URL
#             # The connection factory would normally handle this, but we need to
#             # pass the credential_provider directly to Redis constructor
#             connection_kwargs = self.connection_factory.make_connection_params(server_url)

#             # Replace password-based auth with credential provider
#             connection_kwargs.pop("password", None)  # Remove any password
#             connection_kwargs.pop("username", None)  # Remove any username
#             connection_kwargs.pop("parser_class", None)  # Remove any username
#             connection_kwargs["credential_provider"] = credential_provider
#             connection_kwargs["host"] = "nb021226.redis.cache.windows.net"
#             connection_kwargs["port"] = 6380
#             connection_kwargs["db"] = 1

#             url = connection_kwargs.pop("url", None)
#             # connection_kwargs["host"] = url
#             # Ensure SSL is enabled for Azure Redis
#             if "ssl" not in connection_kwargs:
#                 connection_kwargs["ssl"] = True
#             print(connection_kwargs)
#             # Create and return Redis connection
#             client = Redis(**connection_kwargs)

#             # Test the connection
#             client.ping()
#             logger.info(f"Successfully connected to Redis at index {index}")

#             return client

#         except Exception as e:
#             logger.error(f"Failed to connect to Redis with Azure Managed Identity: {e}")
#             raise RedisConnectionError(f"Azure Redis connection failed: {e}") from e

#     def get_client(self, write: bool = True, tried: Optional[list] = None) -> Redis:
#         """
#         Override get_client to handle token expiration gracefully.

#         If a connection error occurs, it may be due to token expiration.
#         In that case, we'll invalidate the cached credential provider and retry.

#         Args:
#             write: Whether this is a write operation
#             tried: List of already-tried connection indices (for replication)

#         Returns:
#             Redis: Connected Redis client
#         """
#         try:
#             return super().get_client(write=write, tried=tried)
#         except RedisConnectionError as e:
#             # Check if this might be a token expiration issue
#             if self._credential_provider is not None:
#                 logger.warning(f"Redis connection failed, refreshing credential provider: {e}")
#                 # Invalidate the credential provider to force a new token fetch
#                 self._credential_provider = None

#                 # Clear the cached client to force reconnection
#                 index = self.get_next_client_index(write=write, tried=tried)
#                 if self._clients[index] is not None:
#                     self.disconnect(index=index)
#                     self._clients[index] = None

#                 # Retry once with fresh credentials
#                 return super().get_client(write=write, tried=tried)
#             raise
