import argparse
import logging
import os
import re

import yaml

from .migrate_deprecated_templates import replace_deprecated_templates

logger = logging.getLogger(__name__)


def _fix_breadcrumb_items(html: str, stats: dict) -> str:
    """
    Adds 'breadcrumb-item' class to <li> elements within <ol class="breadcrumb"> using regex.
    Modifies the HTML string directly.
    """

    def ol_replacer(ol_match):
        ol_tag = ol_match.group(0)
        # Replace all <li...> inside this <ol>
        ol_tag_new = _add_breadcrumb_item_to_li(ol_tag, stats)
        return ol_tag_new

    # Only operate inside <ol class="breadcrumb">...</ol>
    pattern = re.compile(
        r'<ol\s+class=(["\'])(?:[^"\']*\s)?breadcrumb(?:\s[^"\']*)?\1[^>]*>.*?</ol>', re.DOTALL | re.IGNORECASE
    )
    return pattern.sub(ol_replacer, html)


def _fix_nav_item_to_li(html: str, stats: dict, file_path=None) -> str:
    """
    Adds 'nav-item' class to all <li> tags in the given HTML string,
    and 'nav-link' to <a> or <button> inside, moving 'active' as needed.
    Handles Django template logic for active.
    """

    def li_replacer(match):
        li_tag = match.group(0)
        # If Django template logic is found, notify user and skip auto-fix
        if re.search(r"{%.*%}", li_tag):
            if "manual_nav_template_lines" not in stats:
                stats["manual_nav_template_lines"] = []
            # Get line number and character position of li_tag
            html_lines = html.splitlines()
            for i, line in enumerate(html_lines):
                if li_tag in line:
                    # Append line number, character position and file path for easier identification
                    stats["manual_nav_template_lines"].append(
                        f"{file_path}:{i + 1}:{line.index(li_tag)} - Please review manually '{li_tag}'"
                    )
                    break
            else:
                stats["manual_nav_template_lines"].append(f"{file_path} - Please review manually '{li_tag}'")
            return li_tag

        # Add nav-item to <li>
        class_attr_match = re.search(r'class=(["\'])(.*?)\1', li_tag)
        if class_attr_match:
            classes = class_attr_match.group(2).split()
            if not any("nav-item" in _class for _class in classes):
                classes.append("nav-item")
                stats["nav_items"] += 1
            new_class_attr = f'class="{" ".join(classes)}"'
            li_tag = re.sub(r'class=(["\'])(.*?)\1', new_class_attr, li_tag, count=1)
        else:
            li_tag = re.sub(r"<li(\s|>)", r'<li class="nav-item"\1', li_tag, count=1)
            stats["nav_items"] += 1

        # Move plain active from <li> to child <a> or <button>
        li_tag, n_active = re.subn(
            r'(<li[^>]+)class=(["\'])([^"\']*\bactive\b[^"\']*)\2',
            lambda m: f'{m.group(1)}class="{" ".join([c for c in m.group(3).split() if c != "active"])}"'
            if "active" in m.group(3).split()
            else m.group(0),
            li_tag,
        )
        if n_active:

            def add_active_to_child(child_match):
                child_tag = child_match.group(0)
                child_class_match = re.search(r'class=(["\'])(.*?)\1', child_tag)
                if child_class_match:
                    child_classes = child_class_match.group(2).split()
                    # We use substring rather than exact match for cases with inline Django template fragements like:
                    # <a class="nav-link{% if some_condition %} active{% endif %}">
                    # where our naive split() call above would create "navlink{%" and "active{%" class entries
                    if not any("nav-link" in child_class for child_class in child_classes):
                        child_classes.append("nav-link")
                        stats["nav_items"] += 1
                    if not any("active" in child_class for child_class in child_classes):
                        child_classes.append("active")
                        stats["nav_items"] += 1
                    new_child_class = f'class="{" ".join(child_classes)}"'
                    child_tag = re.sub(r'class=(["\'])(.*?)\1', new_child_class, child_tag, count=1)
                else:
                    child_tag = re.sub(r"<(a|button)", r'<\1 class="nav-link active"', child_tag, count=1)
                    stats["nav_items"] += 1
                return child_tag

            li_tag = re.sub(r"<(a|button)[^>]*>.*?</\1>", add_active_to_child, li_tag, flags=re.DOTALL)

        # Always add nav-link to <a> or <button> if not present
        def add_nav_link(child_match):
            child_tag = child_match.group(0)
            child_class_match = re.search(r'class=(["\'])(.*?)\1', child_tag)
            if child_class_match:
                child_classes = child_class_match.group(2).split()
                if not any("nav-link" in child_class for child_class in child_classes):
                    child_classes.append("nav-link")
                    new_child_class = f'class="{" ".join(child_classes)}"'
                    child_tag = re.sub(r'class=(["\'])(.*?)\1', new_child_class, child_tag, count=1)
            else:
                child_tag = re.sub(r"<(a|button)", r'<\1 class="nav-link"', child_tag, count=1)
            return child_tag

        li_tag = re.sub(r"<(a|button)[^>]*>.*?</\1>", add_nav_link, li_tag, flags=re.DOTALL)

        return li_tag

    return re.sub(r"<li[^>]*>.*?</li>", li_replacer, html, flags=re.DOTALL)


def _fix_nav_tabs_items(html: str, stats: dict, file_path=None) -> str:
    """
    Applies nav-item/nav-link logic to <li> elements within <ul class="nav nav-tabs"> using regex.
    """

    def ul_replacer(ul_match):
        ul_tag = ul_match.group(0)
        ul_tag_new = _fix_nav_item_to_li(ul_tag, stats, file_path=file_path)
        return ul_tag_new

    pattern = re.compile(
        r'<ul\s+class=(["\'])(?:[^"\']*\s)?nav(?:\s[^"\']*)?nav-tabs(?:\s[^"\']*)?\1[^>]*>.*?</ul>',
        re.DOTALL | re.IGNORECASE,
    )
    return pattern.sub(ul_replacer, html)


def _fix_dropdown_lis(html: str, stats: dict, file_path=None) -> str:
    """Adds 'dropdown-item' class to all <li><a>...</a></li> tags in the given HTML string."""

    def a_replacer(match):
        a_tag = match.group(0)
        # If Django template logic is found, notify user and skip auto-fix
        if re.search(r"{%.*%}", a_tag):
            if "manual_nav_template_lines" not in stats:
                stats["manual_nav_template_lines"] = []
            # Get line number and character position of li_tag
            html_lines = html.splitlines()
            for i, line in enumerate(html_lines):
                if a_tag in line:
                    # Append line number, character position and file path for easier identification
                    stats["manual_nav_template_lines"].append(
                        f"{file_path}:{i + 1}:{line.index(a_tag)} - Please review manually '{a_tag}'"
                    )
                    break
            else:
                stats["manual_nav_template_lines"].append(f"{file_path} - Please review manually '{a_tag}'")
            return a_tag

        # Add dropdown-item to <a>
        class_attr_match = re.search(r"""class=(["'])(.*?)\1""", a_tag)
        if class_attr_match:
            classes = class_attr_match.group(2).split()
            if not any("dropdown-item" in _class for _class in classes):
                classes.append("dropdown-item")
                stats["dropdown_items"] += 1
            new_class_attr = f'class="{" ".join(classes)}"'
            a_tag = re.sub(r"""class=(["'])(.*?)\1""", new_class_attr, a_tag, count=1)
        else:
            a_tag = re.sub(r"<a(\s|>)", r'<a class="dropdown-item"\1', a_tag, count=1)
            stats["dropdown_items"] += 1

        return a_tag

    return re.sub("<a[^>]*>.*?</a>", a_replacer, html, flags=re.DOTALL)


def _fix_dropdown_items(html: str, stats: dict, file_path=None) -> str:
    """Ensures that all <li> elements within <ul class="dropdown-menu"> have class="dropdown-item" as appropriate."""

    def ul_replacer(ul_match):
        ul_tag = ul_match.group(0)
        ul_tag_new = _fix_dropdown_lis(ul_tag, stats, file_path=file_path)
        return ul_tag_new

    pattern = re.compile(
        r"""<ul\s+class=(["'])(?:[^"']*\s)?dropdown-menu(?:\s[^"']*)?\1[^>]*>.*?</ul>""",
        re.DOTALL | re.IGNORECASE,
    )
    return pattern.sub(ul_replacer, html)


def _fix_extra_nav_tabs_block(html_string: str, stats: dict, file_path: str) -> str:
    """
    Finds {% block extra_nav_tabs %} blocks and adds nav-item/nav-link to <li> tags inside using regex.
    """
    block_pattern = re.compile(
        r"({%\s*block\s+extra_nav_tabs\s*%})(.*?)({%\s*endblock\s+extra_nav_tabs\s*%})", flags=re.DOTALL | re.IGNORECASE
    )

    def process_match(match):
        block_start_tag = match.group(1)
        block_inner_content = match.group(2)
        block_end_tag = match.group(3)
        new_inner_content = _fix_nav_item_to_li(block_inner_content, stats, file_path=file_path)
        return f"{block_start_tag}{new_inner_content}{block_end_tag}"

    return block_pattern.sub(process_match, html_string)


def _fix_panel_classes(html: str, stats: dict) -> str:
    """
    Converts Bootstrap 3 panel classes to Bootstrap 5 card equivalents using regex.
    Handles panel-primary context for panel-heading.
    """
    # Pattern to match all class attributes
    class_attr_pattern = re.compile(r'class="([^"]*)"')
    # Patterns for exact class matches
    panel_pattern = re.compile(r"\bpanel\b(?!-)")
    panel_color_patterns = {
        "primary": re.compile(r"\bpanel-primary\b"),
        "success": re.compile(r"\bpanel-success\b"),
        "info": re.compile(r"\bpanel-info\b"),
        "warning": re.compile(r"\bpanel-warning\b"),
        "danger": re.compile(r"\bpanel-danger\b"),
    }
    panel_heading_pattern = re.compile(r"\bpanel-heading\b")
    panel_body_pattern = re.compile(r"\bpanel-body\b")
    panel_footer_pattern = re.compile(r"\bpanel-footer\b")
    panel_title_pattern = re.compile(r"\bpanel-title\b")

    result = []
    last = 0
    is_color_panel = False
    panel_color = None

    for match in class_attr_pattern.finditer(html):
        start, end = match.span()
        class_str = match.group(1)
        classes = class_str.split()
        new_classes = []
        changed = False

        if any(panel_pattern.fullmatch(c) for c in classes):
            # If main panel class is found, reset color flag
            is_color_panel = False
            panel_color = None
        # Detect color panel
        for color, color_pat in panel_color_patterns.items():
            if any(color_pat.fullmatch(c) for c in classes):
                is_color_panel = True
                panel_color = color
                break

        for c in classes:
            if panel_pattern.fullmatch(c):
                new_classes.append("card")
                changed = True
                stats["panel_classes"] += 1
            elif any(color_pat.fullmatch(c) for color_pat in panel_color_patterns.values()):
                # Add border color for panel-color
                new_classes.append(f"border-{panel_color}")
                changed = True
                stats["panel_classes"] += 1
            elif panel_heading_pattern.fullmatch(c):
                new_classes.append("card-header")
                changed = True
                stats["panel_classes"] += 1
                if is_color_panel and panel_color:
                    new_classes.append(f"bg-{panel_color}-subtle")
                    new_classes.append(f"border-{panel_color}")
                    new_classes.append("text-body")
            elif panel_body_pattern.fullmatch(c):
                new_classes.append("card-body")
                changed = True
                stats["panel_classes"] += 1
            elif panel_footer_pattern.fullmatch(c):
                new_classes.append("card-footer")
                if is_color_panel and panel_color:
                    new_classes.append(f"bg-{panel_color}-subtle")
                    new_classes.append(f"border-{panel_color}")
                    new_classes.append("text-body")
                changed = True
                stats["panel_classes"] += 1
            elif panel_title_pattern.fullmatch(c):
                new_classes.append("card-title")
                changed = True
                stats["panel_classes"] += 1
            else:
                new_classes.append(c)

        result.append(html[last:start])
        if changed:
            result.append(f'class="{" ".join(new_classes)}"')
        else:
            result.append(match.group(0))
        last = end

    result.append(html[last:])
    return "".join(result)


def _replace_classes(html_string: str, replacements: dict, stats: dict, file_path: str) -> str:
    """
    Replaces class names in html_string according to the replacements dict.
    Each key is replaced with its value using regex word boundaries, case-insensitive.
    Increments stats['replacements'] by the actual number of replacements made.
    """

    def class_attr_replacer(match):
        class_value = match.group(1)
        original = class_value
        if "{%" in class_value or "%}" in class_value:
            if any(
                re.search(r"\b(?<!-)" + re.escape(search) + r"\b(?!-)", class_value) for search in replacements.keys()
            ):
                if "manual_nav_template_lines" not in stats:
                    stats["manual_nav_template_lines"] = []
                stats["manual_nav_template_lines"].append(f"{file_path} - Please review manually '{class_value}'")
        else:
            for search, replace in replacements.items():
                # Only replace whole words in class attribute
                pattern = r"\b(?<!-)" + re.escape(search) + r"\b(?!-)"
                class_value, num_replacements = re.subn(pattern, replace, class_value, flags=re.IGNORECASE)
                if num_replacements > 0:
                    logger.debug(
                        'Replaced "%s" with "%s" (%d times) in class="%s"', search, replace, num_replacements, original
                    )
                    stats["replacements"] += num_replacements
        return f'class="{class_value}"'

    # Only replace within class attributes
    return re.sub(r'class="([^"]*)"', class_attr_replacer, html_string)


def _replace_attributes(html_string: str, replacements: dict, stats: dict) -> str:
    """
    Replaces attribute names in html_string according to the replacements dict.
    Each key is replaced with its value using regex word boundaries, case-insensitive.
    Increments stats['replacements'] by the actual number of replacements made.
    """
    for search, replace in replacements.items():
        # Use re.subn to get the number of replacements
        pattern = r"\b" + re.escape(search) + r"\b"
        html_string, num_replacements = re.subn(pattern, replace, html_string, flags=re.IGNORECASE)
        if num_replacements > 0:
            logger.debug('Replaced "%s" with "%s" (%d times).', search, replace, num_replacements)
            stats["replacements"] += num_replacements
    return html_string


# TODO: Fix this to use regex only, but leaving for now due to the parent span logic. Not necessary for the bootstrap upgrade.
# def _convert_i_to_span_mdi(soup: BeautifulSoup, stats: dict) -> str:
#     """
#     Converts <i> tags with mdi classes to <span> tags.
#     """
#     for icon in soup.find_all('i', class_=re.compile(r'(?<!-)\bmdi\b(?!-)', re.IGNORECASE)):
#         # If parent is already a span, move class and data to parent and remove <i>
#         if icon.parent.name == 'span':
#             # Ensure parent has a class attribute
#             if not icon.parent.has_attr('class'):
#                 icon.parent['class'] = []
#             for class_name in icon.get('class', []):
#                 if class_name not in icon.parent.get('class', []):
#                     icon.parent['class'].append(class_name)
#             for attr, value in icon.attrs.items():
#                 if attr != 'class':
#                     icon.parent[attr] = value
#             icon.decompose()
#             stats['replacements'] += 1
#             continue
#         icon.name = 'span'
#         stats['replacements'] += 1
#         print(f"DEBUG: Converted <i> to <span> for mdi icon: {icon.prettify().strip().splitlines()[0]}...")

#     return str(soup)


def _convert_caret_in_span_to_mdi(html: str, stats: dict) -> str:
    """
    Converts <span> elements with a caret class to use mdi icons.
    Replaces <span class="caret ...">...</span> with <span class="mdi mdi-chevron-down">...</span>
    """
    # Pattern to match <span ...class="...caret...">...</span>
    pattern = re.compile(r'<span([^>]*)class="([^"]*\bcaret\b[^"]*)"([^>]*)>(.*?)</span>', re.DOTALL | re.IGNORECASE)

    def replacer(match):
        before = match.group(1)
        class_attr = match.group(2)
        after = match.group(3)
        inner_html = match.group(4)
        classes = [c for c in class_attr.split() if c != "caret"]
        classes += ["mdi", "mdi-chevron-down"]
        stats["replacements"] += 1
        return f'<span{before}class="{" ".join(classes)}"{after}>{inner_html}</span>'

    return pattern.sub(replacer, html)


def _convert_hover_copy_buttons(html: str, stats: dict) -> str:
    """
    Converts hover copy buttons to the new design (Bootstrap 5).
    """
    # Pattern to match <button ...hover_copy_button...>...</button>
    button_pattern = re.compile(
        r'(<button[^>]*class="[^"]*\bhover_copy_button\b[^"]*"[^>]*>)(.*?)(</button>)', re.DOTALL | re.IGNORECASE
    )

    def button_replacer(match):
        open_tag = match.group(1)
        inner_html = match.group(2)
        close_tag = match.group(3)

        # Fix the class attribute
        def class_replacer(m):
            classes = m.group(1).split()
            classes = [c for c in classes if c != "hover_copy_button"]
            classes = ["btn-secondary" if c == "btn-default" else c for c in classes]
            if "nb-btn-inline-hover" not in classes:
                classes.append("nb-btn-inline-hover")
            return f'class="{" ".join(classes)}"'

        open_tag = re.sub(r'class="([^"]*)"', class_replacer, open_tag)

        # Ensure mdi icon has aria-hidden="true"
        def mdi_replacer(m):
            tag = m.group(0)
            if "aria-hidden=" not in tag:
                tag = tag.replace("<span", '<span aria-hidden="true"', 1)
            return tag

        inner_html = re.sub(r'<span([^>]*)class="([^"]*\bmdi\b[^"]*)"([^>]*)>', mdi_replacer, inner_html)

        # Add visually-hidden Copy span if not present
        if not re.search(
            r'<span[^>]*class="[^"]*\bvisually-hidden\b[^"]*"[^>]*>Copy</span>', inner_html, re.IGNORECASE
        ):
            inner_html += '<span class="visually-hidden">Copy</span>'

        stats["replacements"] += 1
        return f"{open_tag}{inner_html}{close_tag}"

    return button_pattern.sub(button_replacer, html)


def _remove_classes(html: str, classes_to_remove: list[str], stats: dict) -> str:
    """
    Removes each class in classes_to_remove from all class attributes in the HTML string.
    """
    # Build a regex pattern to match any of the classes as a whole word in a class attribute
    pattern = re.compile(r'class="([^"]*)"')

    def class_replacer(match):
        class_attr = match.group(1)
        classes = class_attr.split()
        new_classes = [c for c in classes if c not in classes_to_remove]
        removed = len(classes) - len(new_classes)
        if removed > 0:
            stats["replacements"] += removed
            logger.debug(
                'Removed %d class(es) %s from class="%s" → class="%s"',
                removed,
                classes_to_remove,
                class_attr,
                " ".join(new_classes),
            )
            # If no classes left, remove the class attribute entirely
            if new_classes:
                return f'class="{" ".join(new_classes)}"'
            else:
                return 'class=""'  # Return empty class attribute to be cleaned up later
        return f'class="{class_attr}"'

    # Replace all class attributes in the HTML
    html = pattern.sub(class_replacer, html)
    # Remove empty class attributes and leading whitespace if leading whitespace exists
    html = re.sub(r'\sclass=""', "", html)
    return html


# --- Rule Function (Regex-based for specific block content) ---


def _add_breadcrumb_item_to_li(html: str, stats: dict) -> str:
    """
    Adds 'breadcrumb-item' class to all <li> tags in the given HTML string.
    """

    def li_replacer(match):
        li_tag = match.group(0)
        # If <li> already has class attribute
        class_attr_match = re.search(r'class=(["\'])(.*?)\1', li_tag, flags=re.IGNORECASE)
        if class_attr_match:
            classes = class_attr_match.group(2).split()
            if "breadcrumb-item" not in classes:
                classes.append("breadcrumb-item")
                stats["breadcrumb_items"] += 1
                # Replace the class attribute with the new value
                new_class_attr = f'class="{" ".join(classes)}"'
                li_tag = re.sub(r'class=(["\'])(.*?)\1', new_class_attr, li_tag, flags=re.IGNORECASE)
        else:
            # Add class attribute with breadcrumb-item
            li_tag = re.sub(r"<li", '<li class="breadcrumb-item"', li_tag, count=1)
            stats["breadcrumb_items"] += 1
        return li_tag

    # Replace all <li ...> tags
    return re.sub(r"<li[^>]*>", li_replacer, html)


def _fix_extra_breadcrumbs_block(html_string: str, stats: dict) -> str:
    """
    Finds {% block extra_breadcrumbs %} blocks and adds 'breadcrumb-item' to <li> tags inside using regex.
    """
    block_pattern = re.compile(
        r"({%\s*block\s+extra_breadcrumbs\s*%})(.*?)({%\s*endblock\s+extra_breadcrumbs\s*%})",
        flags=re.DOTALL | re.IGNORECASE,
    )

    def process_match(match):
        block_start_tag = match.group(1)
        block_inner_content = match.group(2)
        block_end_tag = match.group(3)
        new_inner_content = _add_breadcrumb_item_to_li(block_inner_content, stats)
        return f"{block_start_tag}{new_inner_content}{block_end_tag}"

    return block_pattern.sub(process_match, html_string)


def _fix_breadcrumbs_block(html_string: str, stats: dict) -> str:
    """
    Finds {% block breadcrumbs %} blocks and adds 'breadcrumb-item' to <li> tags inside using regex.
    """
    block_pattern = re.compile(
        r"({%\s*block\s+breadcrumbs\s*%})(.*?)({%\s*endblock\s+breadcrumbs\s*%})", flags=re.DOTALL | re.IGNORECASE
    )

    def process_match(match):
        block_start_tag = match.group(1)
        block_inner_content = match.group(2)
        block_end_tag = match.group(3)
        new_inner_content = _add_breadcrumb_item_to_li(block_inner_content, stats)
        return f"{block_start_tag}{new_inner_content}{block_end_tag}"

    return block_pattern.sub(process_match, html_string)


# --- Grid Breakpoints Resize Function ---


def _resize_grid_breakpoints(html_string: str, class_combinations: list[str], stats: dict, file_path: str) -> str:
    """
    Resizes grid breakpoints in `col-*` and `offset-*` classes one step up. Uses given `class_combinations` for known
    class pattern replacements and otherwise does generic xs → sm and md → lg breakpoint resize. In case class list
    contains grid breakpoints other than xs and md, flags it for manual review.
    """
    # Define the breakpoint mapping
    breakpoint_map = {"xs": "sm", "sm": "md", "md": "lg", "lg": "xl", "xl": "xxl"}
    breakpoint_map_keys = list(breakpoint_map.keys())

    if "manual_grid_template_lines" not in stats:
        stats["manual_grid_template_lines"] = []

    def create_grid_class_regex(breakpoints=breakpoint_map_keys):  # pylint: disable=dangerous-default-value
        # Create regex matching Bootstrap grid classes, i.e. `col-*` and `offset-*`, within given breakpoints.
        return re.compile(rf"\b(col|offset)-({'|'.join(breakpoints)})([a-zA-Z0-9-]*)")

    # Resize all given grid `breakpoints` in `string` according to defined `breakpoint_map`
    def resize_breakpoints(string, breakpoints=breakpoint_map_keys, count_stats=False):  # pylint: disable=dangerous-default-value
        def regex_repl(match):
            new_breakpoint = breakpoint_map[match.group(2)]
            if count_stats:
                stats["grid_breakpoints"] += 1
            return f"{match.group(1)}-{new_breakpoint}{match.group(3)}"

        # Replace with regex, e.g., col-xs-12 → col-sm-12
        regex = create_grid_class_regex(breakpoints)
        return regex.sub(regex_repl, string)

    # Resize given `class_combinations` and create an additional joint array from the two. This is required to determine
    # whether a known class combination is present in certain element class list and handle one of the following cases:
    #   1. No, but identified grid breakpoints other than xs and md: flag for manual review.
    #   2. No, and only xs and md grid breakpoints found: generic xs → sm and md → lg replacement.
    #   3. Yes, but has not been resized yet: resize with proper combination.
    #   4. Yes, and has already been resized: do nothing.
    resized_class_combinations = [resize_breakpoints(class_combination) for class_combination in class_combinations]
    known_class_combinations = [*class_combinations, *resized_class_combinations]

    def grid_breakpoints_replacer(match):
        classes = match.group(1)
        # Remove Django template tag blocks, variables and comments and split individual classes into separate strings.
        raw_classes = re.compile(r"{{?((?!{|}).)*}}?").sub(" ", classes).split()
        # Filter out all non-grid classes, keep only `col-*` and `offset-*`.
        grid_class_regex = create_grid_class_regex()
        grid_classes = [cls for cls in raw_classes if grid_class_regex.search(cls)]

        # Check whether given class list consists of any of the known class combinations.
        known_class_combination = None
        for class_combination in known_class_combinations:
            # Look for an exact match, when all classes from given combination are included in element classes and vice versa.
            if all(cls in classes for cls in class_combination.split()) and all(
                grid_class in class_combination for grid_class in grid_classes
            ):
                known_class_combination = class_combination
                break

        if known_class_combination is None:
            # Class combination has not been found.
            if any("xs" not in grid_class and "md" not in grid_class for grid_class in grid_classes):
                # Class list contains grid breakpoints other than xs and md, require manual review.
                linenum = match.string.count("\n", 0, match.start()) + 1
                stats["manual_grid_template_lines"].append(
                    f"{file_path}:{linenum} - Please review manually '{match.group(0)}'"
                )
            else:
                # Class list contains only xs and md grid breakpoints, do generic xs → sm and md → lg replacement
                return f'class="{resize_breakpoints(classes, breakpoints=["xs", "md"], count_stats=True)}"'

        elif known_class_combination not in resized_class_combinations:
            # Class combination has been found, but has not been resized yet: resize with proper combination.
            resized_classes = resized_class_combinations[class_combinations.index(known_class_combination)].split()

            def class_replacer(m):
                current_class = m.group(0)
                stats["grid_breakpoints"] += 1
                return resized_classes[known_class_combination.split().index(current_class)]

            # Replace all classes from given combination by mapping them individually to their resized equivalents.
            return f'class="{re.compile("|".join(known_class_combination.split())).sub(class_replacer, classes)}"'

        # Return unchanged string if conditions above are not satisfied, i.e. do nothing.
        return match.group(0)

    # Find all `class="..."` matches and execute grid breakpoint replacement on them.
    pattern = re.compile(r'class="([^"]*)"')
    return pattern.sub(grid_breakpoints_replacer, html_string)


# --- Main Conversion Function ---


def convert_bootstrap_classes(html_input: str, file_path: str) -> tuple[str, dict]:
    """
    Applies various Bootstrap 3 to 5 conversion rules to the HTML content.
    """
    current_html = html_input  # Start with the original HTML

    # Initialize stats
    stats = {
        "replacements": 0,
        "extra_breadcrumbs": 0,
        "breadcrumb_items": 0,
        "nav_items": 0,
        "dropdown_items": 0,
        "panel_classes": 0,
        "grid_breakpoints": 0,
        "manual_nav_template_lines": [],
        "manual_grid_template_lines": [],
    }

    # --- Stage 1: Apply rules that work directly on the HTML string (simple string/regex replacements) ---
    class_replacements = {
        "pull-left": "float-start",
        "pull-right": "float-end",
        "center-block": "d-block mx-auto",  # Bootstrap 5 uses mx-auto for centering
        "btn-xs": "btn-sm",
        "btn-lg": "btn",  # btn-lg is supported in Bootstrap 5 but not meaningful different from btn in Nautobot's theme
        "btn-default": "btn-secondary",
        "checkbox": "form-check",
        "checkbox-inline": "form-check-input",
        "close": "btn-close",
        "control-label": "col-form-label",
        "dropdown-menu-right": "dropdown-menu-end",
        "form-control-static": "form-control-plaintext",
        "form-group": "mb-10 d-flex justify-content-center",
        "help-block": "form-text",
        "label label-default": "badge bg-default",  # Bootstrap 5 uses general background classes instead of label-default
        "label label-primary": "badge bg-primary",
        "label label-success": "badge bg-success",
        "label label-warning": "badge bg-warning",
        "label label-danger": "badge bg-danger",
        "label label-info": "badge bg-info",
        "label label-transparent": "badge bg-transparent",
        "text-left": "text-start",
        "text-muted": "text-secondary",
        "text-right": "text-end",
        "sr-only": "visually-hidden",  # Bootstrap 5 uses visually-hidden instead of sr-only
        "sr-only-focusable": "visually-hidden-focusable",  # Bootstrap 5 uses visually-hidden-focusable instead of sr-only-focusable
        "accordion-toggle": "nb-collapse-toggle",  # Custom class to handle accordion toggles
        "banner-bottom": "nb-banner-bottom",  # Custom class to handle bottom banners
        "color-block": "nb-color-block",  # Custom class to handle color blocks
        "editor-container": "nb-editor-container",  # Custom class to handle editor containers
        "loading": "nb-loading",  # Custom class to handle loading indicators
        "required": "nb-required",  # Custom class to handle required fields
        "noprint": "d-print-none",  # Bootstrap 5 uses d-print-none instead of noprint
        "report-stats": "nb-report-stats",  # Custom class to handle report stats
        "right-side-panel": "nb-right-side-panel",  # Custom class to handle right side panels
        "software-image-hierarchy": "nb-software-image-hierarchy",  # Custom class to handle software image hierarchy
        "tree-hierarchy": "nb-tree-hierarchy",  # Custom class to handle tree hierarchy
        "tiles": "nb-tiles",  # Custom class
        "tile": "nb-tile",  # Custom class
        "tile-description": "nb-tile-description",  # Custom class
        "tile-footer": "nb-tile-footer",  # Custom class
        "tile-header": "nb-tile-header",  # Custom class
        "table-headings": "nb-table-headings",  # Custom class
        "description": "nb-description",  # Custom class
        "style-line": "nb-style-line",  # Custom class
    }
    # Add column offset fixup, e.g. col-sm-offset-4 --> offset-sm-4
    for bkpt in ["xs", "sm", "md", "lg", "xl", "xxl"]:
        for size in range(0, 13):
            class_replacements[f"col-{bkpt}-offset-{size}"] = f"offset-{bkpt}-{size}"

    attribute_replacements = {
        "data-toggle": "data-bs-toggle",  # Bootstrap 5 uses data-bs-* attributes
        "data-dismiss": "data-bs-dismiss",  # Bootstrap 5 uses data-bs-* attributes
        "data-target": "data-bs-target",  # Bootstrap 5 uses data-bs-* attributes
        "data-title": "data-bs-title",  # Bootstrap 5 uses data-bs-* attributes
        "data-backdrop": "data-bs-backdrop",  # Bootstrap 5 uses data-bs-* attributes
    }

    standard_grid_breakpoint_combinations = [
        "col-md-6 col-sm-6 col-xs-12",  # Rack elevation container: nautobot/dcim/templates/dcim/rack_elevation.html:2
        "col-sm-3 col-md-2 col-md-offset-1",  # Legacy user page nav pills container: nautobot/users/templates/users/base.html:10
        "col-sm-3 col-md-2 offset-md-1",
        "col-sm-4 col-sm-offset-4",  # Selected centered panel containers, e.g. on 404 and 500 error pages and legacy login page: nautobot/core/templates/login.html:54
        "col-sm-4 offset-sm-4",
        "col-sm-4 col-md-3",  # Legacy header search form container: nautobot/core/templates/generic/object_list.html:32
        "col-sm-8 col-md-9 col-sm-12 col-md-12",  # Legacy breadcrumbs container variation on change list page: nautobot/core/templates/admin/change_list.html:33
        "col-sm-8 col-md-9 col-md-12",  # Legacy breadcrumbs container variation on generic object list view page: nautobot/core/templates/generic/object_list.html:13
        "col-sm-8 col-md-9",  # Legacy breadcrumbs container: nautobot/core/templates/generic/object_retrieve.html:16
        "col-sm-9 col-md-8",  # Legacy user page content container: nautobot/users/templates/users/base.html:31
        "col-md-5 col-sm-12",  # Cable trace form left-hand side container: nautobot/dcim/templates/dcim/cable_trace.html:10
        "col-md-7 col-sm-12",  # Cable trace form right-hand side container: nautobot/dcim/templates/dcim/cable_trace.html:86
        "col-lg-6 col-md-6",  # Jinja template/rendered template panel containers: nautobot/core/templates/utilities/render_jinja2.html:29
        "col-md-4 col-lg-8 col-lg-offset-2 col-md-10 col-md-offset-1",  # Standard centered form container variation on generic object bulk update page: nautobot/core/templates/generic/object_bulk_update.html:39
        "col-md-4 col-lg-8 col-lg-offset-2 col-md-10 offset-md-1",
        "col-lg-8 col-lg-offset-2 col-md-10 col-md-offset-1",  # Standard centered form container, e.g. on generic object create page: nautobot/core/templates/generic/object_create.html:12
        "col-lg-8 offset-lg-2 col-md-10 offset-md-1",
    ]

    current_html = _replace_attributes(current_html, attribute_replacements, stats)
    current_html = _replace_classes(current_html, class_replacements, stats, file_path=file_path)
    current_html = _fix_extra_breadcrumbs_block(current_html, stats)
    current_html = _fix_breadcrumbs_block(current_html, stats)
    current_html = _fix_extra_nav_tabs_block(current_html, stats, file_path=file_path)
    current_html = _fix_breadcrumb_items(current_html, stats)
    current_html = _fix_panel_classes(current_html, stats)
    current_html = _remove_classes(
        current_html, ["powered-by-nautobot", "inline-color-block", "panel-default", "hover_copy"], stats
    )  # Remove small form/input classes
    current_html = _convert_caret_in_span_to_mdi(current_html, stats)
    current_html = _convert_hover_copy_buttons(current_html, stats)
    current_html = _fix_nav_tabs_items(current_html, stats, file_path=file_path)
    current_html = _fix_dropdown_items(current_html, stats, file_path=file_path)
    current_html = _resize_grid_breakpoints(current_html, standard_grid_breakpoint_combinations, stats, file_path)

    return current_html, stats


# --- File Processing ---


def fix_html_files_in_directory(directory: str, dry_run=False, skip_templates=False) -> None:
    """
    Recursively finds all .html files in the given directory, applies convert_bootstrap_classes,
    and overwrites each file with the fixed content.
    """

    totals = {
        k: 0
        for k in [
            "replacements",
            "extra_breadcrumbs",
            "breadcrumb_items",
            "nav_items",
            "dropdown_items",
            "panel_classes",
            "grid_breakpoints",
        ]
    }

    if not os.path.exists(directory):
        raise FileNotFoundError(directory)

    if os.path.isfile(directory):
        only_filename = os.path.basename(directory)
        directory = os.path.dirname(directory)
    else:
        only_filename = None

    for root, _, files in os.walk(directory):
        for filename in files:
            if only_filename and only_filename != filename:
                continue
            if filename.lower().endswith(".html"):
                file_path = os.path.join(root, filename)
                logger.info("Processing: %s", file_path)
                with open(file_path, "r", encoding="utf-8") as f:
                    original_content = f.read()

                content = original_content

                fixed_content, stats = convert_bootstrap_classes(content, file_path=file_path)

                if dry_run:
                    logger.info("Would fix: %s", file_path)
                else:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)
                    logger.info("Fixed: %s", file_path)

                if any(stats.values()):
                    print(f"→ {os.path.relpath(file_path, directory)}: ", end="")
                    if stats["replacements"]:
                        print(f"{stats['replacements']} class replacements, ", end="")
                    if stats["extra_breadcrumbs"]:
                        print(f"{stats['extra_breadcrumbs']} extra-breadcrumbs, ", end="")
                    if stats["breadcrumb_items"]:
                        print(f"{stats['breadcrumb_items']} breadcrumb-items, ", end="")
                    if stats["nav_items"]:
                        print(f"{stats['nav_items']} nav-items, ", end="")
                    if stats["dropdown_items"]:
                        print(f"{stats['dropdown_items']} dropdown-items, ", end="")
                    if stats["panel_classes"]:
                        print(f"{stats['panel_classes']} panel replacements, ", end="")
                    if stats["grid_breakpoints"]:
                        print(f"{stats['grid_breakpoints']} grid breakpoint replacements, ", end="")
                    print()

                if stats.get("manual_nav_template_lines"):
                    print("  !!! Manual review needed for nav-item fixes at:")
                    for line in stats["manual_nav_template_lines"]:
                        print(f"    - {line}")
                if stats.get("manual_grid_template_lines"):
                    print("  !!! Manual review needed for non-standard grid breakpoints at:")
                    for line in stats["manual_grid_template_lines"]:
                        print(f"    - {line}")
                for k, v in stats.items():
                    if k in totals:
                        totals[k] += v

    templates_replaced = replace_deprecated_templates(directory, dry_run=dry_run) if not skip_templates else 0

    # Global summary
    total_issues = sum(totals.values())
    print("=== Global Summary ===")
    print(f"Total issues fixed: {total_issues}")
    print(f"- Class replacements:            {totals['replacements']}")
    print(f"- Extra-breadcrumb fixes:        {totals['extra_breadcrumbs']}")
    print(f"- <li> in <ol.breadcrumb>:       {totals['breadcrumb_items']}")
    print(f"- <li> in <ul.nav-tabs>:         {totals['nav_items']}")
    print(f"- <a> in <ul.dropdown-menu>:     {totals['dropdown_items']}")
    print(f"- Panel class replacements:      {totals['panel_classes']}")
    print(f"- Grid breakpoint resizes:       {totals['grid_breakpoints']}")
    print("-------------------------------------")
    print(f"- Deprecated templates replaced: {templates_replaced}")


def check_python_files_for_legacy_html(directory: str):
    exclude_dirs = [
        "__pycache__",
        "node_modules",
    ]
    exclude_files = [
        "bootstrap_v3_to_v5.py",
    ]

    with open(os.path.join(os.path.dirname(__file__), "bootstrap_v3_to_v5_changes.yaml")) as yaml_file:
        try:
            bootstrap_v3_to_v5_changes = yaml.safe_load(yaml_file)
        except yaml.YAMLError:
            print("`bootstrap_v3_to_v5_changes.yaml` file is corrupted.")
            return 1

    def has_multiline_pattern(change):
        return "(?s)" in change["Search Regex"][1:-2]

    multiline_pattern_changes = [change for change in bootstrap_v3_to_v5_changes if has_multiline_pattern(change)]
    standard_pattern_changes = [change for change in bootstrap_v3_to_v5_changes if not has_multiline_pattern(change)]

    matches = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            if filename in exclude_files or not filename.endswith(".py"):
                continue
            with open(os.path.join(dirpath, filename), "rt") as fh:
                contents = fh.readlines()
                full_contents = "".join(contents)

            for linenum, line in enumerate(contents, start=1):
                for change in standard_pattern_changes:
                    if re.search(change["Search Regex"][1:-2], line):
                        print(f"{os.path.join(dirpath, filename)}({linenum}):\t{line}\t:\t{change['Bootstrap v5']}")
                    matches += 1
            for change in multiline_pattern_changes:
                multiline_matches = re.finditer(change["Search Regex"][1:-2], full_contents)
                for multiline_match in multiline_matches:
                    linenum = multiline_match.string.count("\n", 0, multiline_match.start()) + 1
                    substring = multiline_match.string[multiline_match.start() : multiline_match.end()]
                    print(f"{os.path.join(dirpath, filename)}({linenum}):\t{substring}\n\t:\t{change['Bootstrap v5']}")
                    matches += 1
            for exclude_dir in exclude_dirs:
                if exclude_dir in dirnames:
                    dirnames.remove(exclude_dir)

    return matches


def main():
    parser = argparse.ArgumentParser(description="Bootstrap 3 to 5 HTML fixer.")
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Show which files would be modified without making any changes.",
    )
    parser.add_argument("path", type=str, help="Path to directory in which to recursively fix all .html files.")
    parser.add_argument(
        "-st", "--skip-template-replacement", action="store_true", help="Skip replacing deprecated templates."
    )
    parser.add_argument("-p", "--check-python-files", action="store_true", help="Check Python files for legacy HTML.")
    parser.add_argument("--no-fix-html-templates", action="store_true", help="Do not fix HTML template files.")
    args = parser.parse_args()

    exit_code = 0
    if args.check_python_files:
        exit_code = check_python_files_for_legacy_html(args.path)
    if not args.no_fix_html_templates:
        fix_html_files_in_directory(args.path, dry_run=args.dry_run, skip_templates=args.skip_template_replacement)

    return exit_code


if __name__ == "__main__":
    main()
