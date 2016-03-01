from django.core.paginator import Paginator, Page


class EnhancedPaginator(Paginator):

    def _get_page(self, *args, **kwargs):
        return EnhancedPage(*args, **kwargs)


class EnhancedPage(Page):

    def smart_pages(self):
        """
        Instead of every page, return only first, last, and nearby pages (taken from
        https://www.technovelty.org/web/skipping-pages-with-djangocorepaginator.html).
        """
        n = self.number
        last_page = self.paginator.num_pages

        # Determine the page numbers to display
        pages_wanted = [1, 2, n-2, n-1, n, n+1, n+2, last_page-1, last_page]
        pages_to_show = set(self.paginator.page_range).intersection(pages_wanted)
        pages_to_show = sorted(pages_to_show)

        # Insert skip markers
        skip_pages = [x[1] for x in zip(pages_to_show[:-1], pages_to_show[1:]) if (x[1] - x[0] != 1)]
        for i in skip_pages:
            pages_to_show.insert(pages_to_show.index(i), False)

        return pages_to_show
