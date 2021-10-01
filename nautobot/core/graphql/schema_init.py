import hashlib
import json

from django.db.models import signals
import graphene
from graphene_django.types import ObjectType
import redis

from .schema import generate_query_mixin
from nautobot.core.settings_funcs import parse_redis_connection
from nautobot.extras.models import CustomField, Relationship


schema = None


def schema_hash(schema):
    return hashlib.md5(json.dumps(schema.introspect(), sort_keys=True).encode("utf-8")).hexdigest()


def redis_hash_changed():
    hsh = schema_hash(schema)
    r = redis.from_url(parse_redis_connection(0))

    return r.get("nautobot_graphql_schema_hash") == hsh


def redis_set():
    hsh = schema_hash(schema)
    r = redis.from_url(parse_redis_connection(0))

    r.set("nautobot_graphql_schema_hash", hsh)


# manipulating the global is less than pretty, but it’s the only way to enable
# the state of the app from signals that might just be what we have to do
def generate_schema(*args, **kwargs):
    DynamicGraphQL = generate_query_mixin()

    global schema
    Query = type("Query", (ObjectType, DynamicGraphQL), {})

    schema = graphene.Schema(query=Query, auto_camelcase=False)

    # how to deal with the race condition that since generation a new
    # relationship was generated? fixpoint logic used here, might not
    # terminate
    if redis_hash_changed():
        generate_schema()
    else:
        redis_set()


# generate the initial schema
generate_schema()


def get_schema():
    if redis_hash_changed():
        generate_schema()

    return schema


signals.post_save.connect(generate_schema, sender=Relationship)
signals.post_delete.connect(generate_schema, sender=Relationship)
signals.post_save.connect(generate_schema, sender=CustomField)
signals.post_delete.connect(generate_schema, sender=CustomField)
