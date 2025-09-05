"""Utilities for apps to implement test automation."""

from nautobot.core.testing import (
    create_job_result_and_run_job,
    get_job_class_and_model,
    run_job_for_testing,
    TransactionTestCase,
)
from nautobot.core.testing.api import APITestCase, APITransactionTestCase, APIViewTestCases
from nautobot.core.testing.filters import FilterTestCases
from nautobot.core.testing.forms import FormTestCases
from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.core.testing.migrations import NautobotDataMigrationTest
from nautobot.core.testing.mixins import NautobotTestCaseMixin, NautobotTestClient
from nautobot.core.testing.models import ModelTestCases
from nautobot.core.testing.schema import OpenAPISchemaTestCases
from nautobot.core.testing.utils import (
    create_test_user,
    disable_warnings,
    extract_form_failures,
    extract_page_body,
    generate_random_device_asset_tag_of_specified_size,
    get_deletable_objects,
    post_data,
)
from nautobot.core.testing.views import ModelTestCase, ModelViewTestCase, TestCase, ViewTestCases

__all__ = (
    "APITestCase",
    "APITransactionTestCase",
    "APIViewTestCases",
    "FilterTestCases",
    "FormTestCases",
    "ModelTestCase",
    "ModelTestCases",
    "ModelViewTestCase",
    "NautobotDataMigrationTest",
    "NautobotTestCaseMixin",
    "NautobotTestClient",
    "OpenAPISchemaTestCases",
    "SeleniumTestCase",
    "TestCase",
    "TransactionTestCase",
    "ViewTestCases",
    "create_job_result_and_run_job",
    "create_test_user",
    "disable_warnings",
    "extract_form_failures",
    "extract_page_body",
    "generate_random_device_asset_tag_of_specified_size",
    "get_deletable_objects",
    "get_job_class_and_model",
    "post_data",
    "run_job_for_testing",
)
