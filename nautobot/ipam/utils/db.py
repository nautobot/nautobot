"""Wrapper functions for custom database functions used by IPAM."""

from django.db import models
from django.db.models import Func


class ByteaToIPString(Func):
    function = "bytea_to_ip_string"
    output_field = models.TextField()
