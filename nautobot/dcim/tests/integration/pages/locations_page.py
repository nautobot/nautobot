"""Page object for the Locations list view (/dcim/locations/)."""

from nautobot.playwright.list_page import ListPage


class LocationsPage(ListPage):
    """The Locations list view. List and filter-drawer behavior comes from ListPage."""

    LIST_PATH = "/dcim/locations/"

    def filter_by_parent(self, parent_name):
        """Open the filter drawer and apply a parent filter for *parent_name*.

        Location options in the parent picker render their full ancestry path
        (e.g. "Region → Site"), so the option text is matched as a substring. The
        substring cannot hit a child of the target instead: Select2 search is
        server-side on the location name, and a child's name does not contain its
        parent's, so only the parent comes back for a full-name search.
        """
        self.open_filter_drawer()
        self.pick_filter_value("parent", parent_name, exact=False)
        self.apply_filters()
