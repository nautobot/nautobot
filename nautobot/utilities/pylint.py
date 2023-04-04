import inspect

from astroid import ClassDef, Assign, Const, Attribute
from django.db.models import Model
from django.forms import Form
from django_filters import FilterSet
from pylint.checkers import BaseChecker

from nautobot.core.models import BaseModel
from nautobot.utilities.filters import BaseFilterSet
from nautobot.utilities.forms import BootstrapMixin


def to_path(obj):
    """Given an object, return its fully qualified import path."""
    return f"{inspect.getmodule(obj).__name__}.{obj.__name__}"


def is_abstract(node):
    """Given a node, returns whether it is an abstract base model."""
    for child_node in node.get_children():
        if not (isinstance(child_node, ClassDef) and child_node.name == "Meta"):
            continue
        for meta_child in child_node.get_children():
            if (
                not isinstance(meta_child, Assign)
                or not meta_child.targets[0].name == "abstract"
                or not isinstance(meta_child.value, Const)
            ):
                continue
            # At this point we know we are dealing with an assignment to a constant for the 'abstract' field on the
            # 'Meta' class. Therefore, we can assume the value of that to be whether the node is an abstract base model
            # or not.
            return meta_child.value.value
    return False


class ModelExistenceChecker(BaseChecker):

    name = "nautobot-model-existence"
    msgs = {
        "W5002": (
            "Use instance.present_in_database",
            "wrong-presence-check",
            "Model existence in the database should be checked with 'instance.present_in_database'.",
        )
    }

    def visit_if(self, node):
        for child in node.get_children():
            if isinstance(child, Attribute) and child.attrname == "pk":
                self.add_message(
                    msgid="wrong-presence-check",
                    line=child.lineno,
                    node=node,
                    col_offset=child.col_offset,
                    end_lineno=child.end_lineno,
                    end_col_offset=child.end_col_offset,
                )


class BaseClassChecker(BaseChecker):

    # Maps a non-Nautobot-specific base class to a Nautobot-specific base classes which has to be in the class hierarchy
    # for every class that has the base class in its hierarchy.
    external_to_nautobot_class_mapping = [
        (to_path(FilterSet), to_path(BaseFilterSet)),
        (to_path(Model), to_path(BaseModel)),
        (to_path(Form), to_path(BootstrapMixin)),
    ]

    name = "nautobot-base-class"
    msgs = {
        "W5001": (
            "Uses correct base classes.",
            "incorrect-base-class",
            "All classes should inherit from the correct base classes.",
        )
    }

    def visit_classdef(self, node):
        if is_abstract(node):
            return

        # Skip mixin classes
        if "Mixin" in node.name:
            return

        ancestor_class_types = [ancestor.qname() for ancestor in node.ancestors()]
        for base_class, nautobot_base_class in self.external_to_nautobot_class_mapping:
            if base_class in ancestor_class_types and nautobot_base_class not in ancestor_class_types:
                self.add_message(msgid="incorrect-base-class", node=node)


def register(linter):
    linter.register_checker(BaseClassChecker(linter))
    linter.register_checker(ModelExistenceChecker(linter))
