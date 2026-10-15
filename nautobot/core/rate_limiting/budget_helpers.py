import hashlib

from django_redis import get_redis_connection

CREDENTIAL_DIGEST_LENGTH = 16
NO_EXPIRY_SET = -1


def hash_user_identifier(user_identifier):
    utf8_encoded_identifier = user_identifier.encode("utf-8")
    sha256_identifier = hashlib.sha256(utf8_encoded_identifier)
    hexdigest = sha256_identifier.hexdigest()
    truncated_hexdigest = hexdigest[:CREDENTIAL_DIGEST_LENGTH]

    return truncated_hexdigest


def get_rate_limit_bucket_id(user_token):
    hashed_user_identifier = hash_user_identifier(user_token)
    user_rate_limit_bucket_id = f"user_token:{hashed_user_identifier}"

    return user_rate_limit_bucket_id


def charge_bucket(bucket_id, cost, timeout):
    """Charges the specified Redis bucket, using the specified `bucket_id` and `cost`.

    Makes an attempt to charge a Redis bucket. If bucket does not exist it is created with the `timeout` provided. If it does exist `timeout` is not modified. The `cost` is applied every time on new bucket or existing bucket.

    Args:
        bucket_id (string): The bucket to charge
        cost (int): The cost charge to charge the bucket
        timeout (int): The timeout to specify for this bucket in Redis

    Returns:
        (consumed_budget, remaining_timeout): A tuple containing the rate limiting budget consumed in the Redis bucket, and the remaining time that bucket will exist for.
    """
    connection = get_redis_connection("default")

    pipeline = connection.pipeline()
    pipeline.incrby(bucket_id, cost)
    pipeline.ttl(bucket_id)
    consumed_budget, remaining_timeout = pipeline.execute()

    if remaining_timeout == NO_EXPIRY_SET:
        connection.expire(bucket_id, timeout)
        remaining_timeout = timeout

    return consumed_budget, remaining_timeout
