from nautobot.extras.api.serializers import NautobotModelSerializer
from nautobot.extras.validation_engine.models import ValidationResult

class ValidationResultSerializer(NautobotModelSerializer):

    class Meta:
        model = ValidationResult
        fields = "__all__"