from rest_framework import serializers

from extras.models import Graph


class GraphSerializer(serializers.ModelSerializer):
    embed_url = serializers.SerializerMethodField()

    class Meta:
        model = Graph
        fields = ['name', 'embed_url', 'link']

    def get_embed_url(self, obj):
        return obj.embed_url(self.context['graphed_object'])
