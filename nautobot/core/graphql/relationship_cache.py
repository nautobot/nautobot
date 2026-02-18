"""Simple request-scoped cache for relationship associations."""

from collections import defaultdict
import logging

from nautobot.extras.choices import RelationshipSideChoices
from nautobot.extras.models import RelationshipAssociation

logger = logging.getLogger(__name__)


def get_relationship_peer_ids(obj_id, relationship, side, context):
    """Get peer IDs for a relationship, using request-scoped cache."""
    if not hasattr(context, "_relationship_cache"):
        context._relationship_cache = {}

    cache_key = (relationship.id, side)

    if cache_key not in context._relationship_cache:
        logger.debug(f"Caching associations for relationship={relationship.key}, side={side}")
        context._relationship_cache[cache_key] = defaultdict(list)
        peer_side = RelationshipSideChoices.OPPOSITE[side]

        if relationship.symmetric:
            for src_id, dst_id in RelationshipAssociation.objects.filter(
                relationship=relationship
            ).values_list("source_id", "destination_id"):
                context._relationship_cache[cache_key][src_id].append(dst_id)
                context._relationship_cache[cache_key][dst_id].append(src_id)
        else:
            for src_id, peer_id in RelationshipAssociation.objects.filter(
                relationship=relationship
            ).values_list(f"{side}_id", f"{peer_side}_id"):
                context._relationship_cache[cache_key][src_id].append(peer_id)

    return context._relationship_cache[cache_key].get(obj_id, [])


def get_cached_peer_objects(peer_ids, peer_model, relationship, side, user, context):
    """Get peer objects, caching all on first access."""
    if not peer_ids:
        return []

    if not hasattr(context, "_peer_objects_cache"):
        context._peer_objects_cache = {}

    cache_key = (relationship.id, side, peer_model.__name__)

    if cache_key not in context._peer_objects_cache:
        assoc_key = (relationship.id, side)
        all_peer_ids = set()
        for pids in context._relationship_cache.get(assoc_key, {}).values():
            all_peer_ids.update(pids)

        if all_peer_ids:
            logger.debug(f"Caching {len(all_peer_ids)} peer objects for {peer_model.__name__}")
            queryset = peer_model.objects.filter(id__in=all_peer_ids)
            if hasattr(queryset, "restrict"):
                queryset = queryset.restrict(user, "view")
            context._peer_objects_cache[cache_key] = {obj.id: obj for obj in queryset}
        else:
            context._peer_objects_cache[cache_key] = {}

    return [context._peer_objects_cache[cache_key][pid] for pid in peer_ids if pid in context._peer_objects_cache[cache_key]]
