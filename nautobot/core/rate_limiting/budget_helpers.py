import hashlib

from django_redis import get_redis_connection
import redis.exceptions

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
    try:
        connection = get_redis_connection("default")

        pipeline = connection.pipeline()
        pipeline.incrby(bucket_id, cost)
        pipeline.ttl(bucket_id)
        consumed_budget, remaining_timeout = pipeline.execute()

        if remaining_timeout == NO_EXPIRY_SET:
            connection.expire(bucket_id, timeout)
            remaining_timeout = timeout

        return consumed_budget, remaining_timeout
    except redis.exceptions.RedisError:
        return None, None
