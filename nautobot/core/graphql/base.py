from graphene_django import DjangoObjectType


class NautobotObjectType(DjangoObjectType):
    def __init_subclass__(cls, **kwargs):
        cls._cached_meta = cls.Meta
        super().__init_subclass__(**kwargs)

    class Meta:
        abstract = True
