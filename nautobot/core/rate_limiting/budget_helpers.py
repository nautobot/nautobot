import hashlib
import math

from django.core.cache import cache
import redis.exceptions

CREDENTIAL_DIGEST_LENGTH = 16
TOKEN_BUCKET_SCHEME = "user_token"  # noqa: S105 - Not sensitive data


def hash_user_identifier(user_identifier):
    utf8_encoded_identifier = user_identifier.encode("utf-8")
    sha256_identifier = hashlib.sha256(utf8_encoded_identifier)
    hexdigest = sha256_identifier.hexdigest()
    truncated_hexdigest = hexdigest[:CREDENTIAL_DIGEST_LENGTH]

    return truncated_hexdigest


def get_user_rate_limit_bucket_id(user_token, window):
    hashed_user_identifier = hash_user_identifier(user_token)
    user_rate_limit_bucket_id = f"{TOKEN_BUCKET_SCHEME}:{hashed_user_identifier}:{window}"

    return user_rate_limit_bucket_id


def get_time_window(current_time, window_duration):
    time_window_id = int(current_time // window_duration)

    return time_window_id


def get_seconds_remaining_in_window(current_time, window_duration):
    elapsed_seconds_in_window = current_time % window_duration
    remaining_seconds_in_window = window_duration - elapsed_seconds_in_window
    whole_remaining_seconds = math.ceil(remaining_seconds_in_window)
    floored_remaining_seconds = max(1, whole_remaining_seconds)

    return floored_remaining_seconds


def charge_bucket(bucket_id, cost, timeout):
    try:
        cache.incr(bucket_id, cost, ignore_key_check=True)
        cache.touch(bucket_id, timeout)
        return None
    except redis.exceptions.RedisError:
        return None


def get_current_bucket(bucket_id):
    try:
        return cache.get(bucket_id, 0)
    except redis.exceptions.RedisError:
        return None
