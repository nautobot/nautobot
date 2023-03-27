from django.db import models
from django.shortcuts import reverse
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from nautobot.core.models import BaseModel

class ValidationResult(BaseModel):
    class_name = models.CharField(max_length=100)
    function_name = models.CharField(max_length=100)
    last_validation_date = models.DateField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=200)
    validated_object = GenericForeignKey("content_type", "object_id")
    validated_object_attribute = models.CharField(max_length=100)
    validated_object_value = models.CharField(max_length=100, null=True)
    valid = models.BooleanField()
    message = models.CharField(max_length=100, null=True)
