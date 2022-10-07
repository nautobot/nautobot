from django.test import TestCase


class SearchFormTestCase(TestCase):
    def test_q_placeholder(self):
        from nautobot.core.forms import SearchForm

        self.assertEqual(SearchForm().fields["q"].widget.attrs["placeholder"], "Search")

        # Assert the q field placeholder is overridden
        self.assertEqual(
            SearchForm(q_placeholder="Search Sites").fields["q"].widget.attrs["placeholder"], "Search Sites"
        )
