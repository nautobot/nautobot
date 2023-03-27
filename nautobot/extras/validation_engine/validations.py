import inspect
from datetime import datetime
from django.contrib.contenttypes.models import ContentType
from django.apps import apps as global_apps
from nautobot.extras.validation_engine.models import ValidationResult

class ValidationSet():
    name: str
    model: str

    def __generate_result(self, valid, obj, attr, value, message):
        field_names = [f.name for f in obj._meta.get_fields()]
        if attr not in field_names: 
            raise Exception(f"Validated object does not have attribute {attr}.")
        function_name = inspect.stack()[2].function
        content_type = ContentType.objects.get_for_model(obj)
        result = ValidationResult.objects.filter(
            class_name = self.name, 
            function_name = function_name, 
            content_type = content_type, 
            object_id = obj.id, 
            validated_object_attribute = attr
        ).all()
        if len(result) > 1:
            raise Exception(f"Multiple ValidationResults exist for {self.name}:{function_name}:{str(obj)}.")
        if result:
            result = result[0]
            result.last_validation_date = datetime.now()
            result.validated_object_value = str(value)
            result.valid = valid
            result.message = message
        else:
            result = ValidationResult(
                class_name = self.name,
                function_name = function_name,
                last_validation_date = datetime.now(),
                validated_object = obj,
                validated_object_attribute = attr,
                validated_object_value = str(value),
                valid = valid,
                message = message,
            )
        result.save()

    def success(self, obj, attr, value, message=None):
        return self.__generate_result(True, obj, attr, value, message)

    def fail(self, obj, attr, value, message):
        return self.__generate_result(False, obj, attr, value, message)

    def get_queryset(self):
        model = global_apps.get_model(self.model)
        return model.objects.all()

    def validate(self):
        validation_functions = [function for name, function in inspect.getmembers(self, predicate=inspect.ismethod) if name.startswith('validate_')]
        for obj in self.get_queryset():
            for function in validation_functions:
                function(obj)
