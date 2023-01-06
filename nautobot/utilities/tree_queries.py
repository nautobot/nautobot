

class TreeModel(TreeNode):
    """
    Nautobot-specific base class for models that exist in a self-referential tree.
    """

    objects = TreeManager()

    class Meta:
        abstract = True

    @property
    def display(self):
        """By default, TreeModels display their full ancestry for clarity."""
        if not hasattr(self, "name"):
            raise NotImplementedError("default TreeModel.display implementation requires a `name` attribute!")
        display_str = ""
        try:
            for ancestor in self.ancestors():
                display_str += ancestor.name + " → "
        except self.DoesNotExist:
            # Expected to occur at times during bulk-delete operations
            pass
        finally:
            display_str += self.name
            return display_str  # pylint: disable=lost-exception
