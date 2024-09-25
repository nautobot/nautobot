"""Base classes and utilities for defining the Nautobot home page."""

from abc import ABC, abstractmethod

from .base import PermissionsMixin


class HomePageBase(ABC):
    """Base class for homepage layout classes."""

    @property
    @abstractmethod
    def initial_dict(self):  # to be implemented by each subclass
        return {}

    @property
    @abstractmethod
    def fixed_fields(self):  # to be implemented by subclass
        return ()


class HomePagePanel(HomePageBase, PermissionsMixin):
    """Defines properties that can be used for a panel."""

    items = None
    template_path = None

    @property
    def initial_dict(self):
        return {
            "custom_template": self.custom_template,
            "custom_data": self.custom_data,
            "weight": self.weight,
            "items": {},
            "permissions": self.permissions,
            "template_path": self.template_path,
        }

    @property
    def fixed_fields(self):
        return ()

    def __init__(self, name, permissions=None, custom_data=None, custom_template=None, items=None, weight=1000):
        """
        Ensure panel properties.

        Args:
            name (str): The name of the panel.
            permissions (list): The permissions required to view this panel.
            custom_data (dict): Custom data to be passed to the custom template.
            custom_template (str): Name of custom template.
            items (list): List of items to be rendered in this panel.
            weight (int): The weight of this panel.
        """
        super().__init__(permissions)
        self.custom_data = custom_data
        self.custom_template = custom_template
        self.name = name
        self.weight = weight

        if items is not None and custom_template is not None:
            raise ValueError("Cannot specify items and custom_template at the same time.")
        if items is not None:
            if not isinstance(items, (list, tuple)):
                raise TypeError("Items must be passed as a tuple or list.")
            elif not all(isinstance(item, (HomePageGroup, HomePageItem)) for item in items):
                raise TypeError("All items defined in a panel must be an instance of HomePageGroup or HomePageItem")
            self.items = items
        else:
            self.items = []


class HomePageGroup(HomePageBase, PermissionsMixin):
    """Defines properties that can be used for a panel group."""

    items = []

    @property
    def initial_dict(self):
        return {
            "items": {},
            "permissions": self.permissions,
            "weight": self.weight,
        }

    @property
    def fixed_fields(self):
        return ()

    def __init__(self, name, permissions=None, items=None, weight=1000):
        """
        Ensure group properties.

        Args:
            name (str): The name of the group.
            permissions (list): The permissions required to view this group.
            items (list): List of items to be rendered in this group.
            weight (int): The weight of this group.
        """
        super().__init__(permissions)
        self.name = name
        self.weight = weight

        if items is not None:
            if not isinstance(items, (list, tuple)):
                raise TypeError("Items must be passed as a tuple or list.")
            elif not all(isinstance(item, HomePageItem) for item in items):
                raise TypeError("All items defined in a group must be an instance of HomePageItem")
            self.items = items


class HomePageItem(HomePageBase, PermissionsMixin):
    """Defines properties that can be used for a panel item."""

    items = []
    template_path = None

    @property
    def initial_dict(self):
        return {
            "custom_template": self.custom_template,
            "custom_data": self.custom_data,
            "description": self.description,
            "link": self.link,
            "model": self.model,
            "permissions": self.permissions,
            "template_path": self.template_path,
            "weight": self.weight,
        }

    @property
    def fixed_fields(self):
        return ()

    def __init__(
        self,
        name,
        link=None,
        model=None,
        custom_template=None,
        custom_data=None,
        description=None,
        permissions=None,
        weight=1000,
    ):
        """
        Ensure item properties.

        Args:
            name (str): The name of the item.
            link (str): The link to be used for this item.
            model (str): The model to being used for this item to calculate the total count of objects.
            custom_template (str): Name of custom template.
            custom_data (dict): Custom data to be passed to the custom template.
        """
        super().__init__(permissions)

        self.name = name
        self.custom_template = custom_template
        self.custom_data = custom_data
        self.description = description
        self.link = link
        self.model = model
        self.weight = weight

        if model is not None and custom_template is not None:
            raise ValueError("Cannot specify model and custom_template at the same time.")
