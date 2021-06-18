from django.test import tag, TransactionTestCase as _TransactionTestCase

from .api import *
from .utils import *
from .views import *


@tag("unit")
class TransactionTestCase(_TransactionTestCase):
    """
    Base test case class using the TransactionTestCase for unit testing
    """
