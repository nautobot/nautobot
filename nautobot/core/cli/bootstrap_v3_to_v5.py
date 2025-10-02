import argparse
import logging
import os
import re

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
        r'<ol\s+class=(["\'])(?:[^"\']*\s)?breadcrumb(?:\s[^"\']*)?\1[^>]*>.*?</ol>',
        re.DOTALL | re.IGNORECASE
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
        if re.search(r'{%.*%}', li_tag):
            if 'manual_nav_template_lines' not in stats:
                stats['manual_nav_template_lines'] = []
            # Get line number and character position of li_tag
            html_lines = html.splitlines()
            for i, line in enumerate(html_lines):
                if li_tag in line:
                    # Append line number, character position and file path for easier identification
                    stats['manual_nav_template_lines'].append(f"{file_path}:{i + 1}:{line.index(li_tag)} - Please review manually '{li_tag}'")
                    break
            else:
                stats['manual_nav_template_lines'].append(f"{file_path} - Please review manually '{li_tag}'")
            return li_tag

        # Add nav-item to <li>
        class_attr_match = re.search(r'class=(["\'])(.*?)\1', li_tag)
        if class_attr_match:
            classes = class_attr_match.group(2).split()
            if not any(['nav-item' in _class for _class in classes]):
                classes.append('nav-item')
                stats['nav_items'] += 1
            new_class_attr = f'class="{" ".join(classes)}"'
            li_tag = re.sub(r'class=(["\'])(.*?)\1', new_class_attr, li_tag, count=1)
        else:
            li_tag = re.sub(r'<li(\s|>)', r'<li class="nav-item"\1', li_tag, count=1)
            stats['nav_items'] += 1

        # Move plain active from <li> to child <a> or <button>
        li_tag, n_active = re.subn(
            r'(<li[^>]+)class=(["\'])([^"\']*\bactive\b[^"\']*)\2',
            lambda m: f'{m.group(1)}class="{ " ".join([c for c in m.group(3).split() if c != "active"]) }"' if "active" in m.group(3).split() else m.group(0),
            li_tag
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
                    if not any(["nav-link" in child_class for child_class in child_classes]):
                        child_classes.append('nav-link')
                        stats['nav_items'] += 1
                    if not any(["active" in child_class for child_class in child_classes]):
                        child_classes.append('active')
                        stats['nav_items'] += 1
                    new_child_class = f'class="{" ".join(child_classes)}"'
                    child_tag = re.sub(r'class=(["\'])(.*?)\1', new_child_class, child_tag, count=1)
                else:
                    child_tag = re.sub(r'<(a|button)', r'<\1 class="nav-link active"', child_tag, count=1)
                    stats['nav_items'] += 1
                return child_tag
            li_tag = re.sub(r'<(a|button)[^>]*>.*?</\1>', add_active_to_child, li_tag, flags=re.DOTALL)

        # Always add nav-link to <a> or <button> if not present
        def add_nav_link(child_match):
            child_tag = child_match.group(0)
            child_class_match = re.search(r'class=(["\'])(.*?)\1', child_tag)
            if child_class_match:
                child_classes = child_class_match.group(2).split()
                if not any(["nav-link" in child_class for child_class in child_classes]):
                    child_classes.append('nav-link')
                    new_child_class = f'class="{" ".join(child_classes)}"'
                    child_tag = re.sub(r'class=(["\'])(.*?)\1', new_child_class, child_tag, count=1)
            else:
                child_tag = re.sub(r'<(a|button)', r'<\1 class="nav-link"', child_tag, count=1)
            return child_tag
        li_tag = re.sub(r'<(a|button)[^>]*>.*?</\1>', add_nav_link, li_tag, flags=re.DOTALL)

        return li_tag

    return re.sub(r'<li[^>]*>.*?</li>', li_replacer, html, flags=re.DOTALL)

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
        re.DOTALL | re.IGNORECASE
    )
    return pattern.sub(ul_replacer, html)

def _fix_extra_nav_tabs_block(html_string: str, stats: dict, file_path: str = None) -> str:
    """
    Finds {% block extra_nav_tabs %} blocks and adds nav-item/nav-link to <li> tags inside using regex.
    """
    block_pattern = re.compile(
        r'({%\s*block\s+extra_nav_tabs\s*%})(.*?)({%\s*endblock\s+extra_nav_tabs\s*%})',
        flags=re.DOTALL | re.IGNORECASE
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
    panel_pattern = re.compile(r'\bpanel\b(?!-)')
    panel_color_patterns = {
        'primary': re.compile(r'\bpanel-primary\b'),
        'success': re.compile(r'\bpanel-success\b'),
        'info': re.compile(r'\bpanel-info\b'),
        'warning': re.compile(r'\bpanel-warning\b'),
        'danger': re.compile(r'\bpanel-danger\b'),
    }
    panel_heading_pattern = re.compile(r'\bpanel-heading\b')
    panel_body_pattern = re.compile(r'\bpanel-body\b')
    panel_footer_pattern = re.compile(r'\bpanel-footer\b')
    panel_title_pattern = re.compile(r'\bpanel-title\b')

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
                new_classes.append('card')
                changed = True
                stats['panel_classes'] += 1
            elif any(color_pat.fullmatch(c) for color_pat in panel_color_patterns.values()):
                # Add border color for panel-color
                new_classes.append(f'border-{panel_color}')
                changed = True
                stats['panel_classes'] += 1
            elif panel_heading_pattern.fullmatch(c):
                new_classes.append('card-header')
                changed = True
                stats['panel_classes'] += 1
                if is_color_panel and panel_color:
                    new_classes.append(f'bg-{panel_color}-subtle')
                    new_classes.append(f'border-{panel_color}')
                    new_classes.append('text-body')
            elif panel_body_pattern.fullmatch(c):
                new_classes.append('card-body')
                changed = True
                stats['panel_classes'] += 1
            elif panel_footer_pattern.fullmatch(c):
                new_classes.append('card-footer')
                if is_color_panel and panel_color:
                    new_classes.append(f'bg-{panel_color}-subtle')
                    new_classes.append(f'border-{panel_color}')
                    new_classes.append('text-body')
                changed = True
                stats['panel_classes'] += 1
            elif panel_title_pattern.fullmatch(c):
                new_classes.append('card-title')
                changed = True
                stats['panel_classes'] += 1
            else:
                new_classes.append(c)

        result.append(html[last:start])
        if changed:
            result.append(f'class="{" ".join(new_classes)}"')
        else:
            result.append(match.group(0))
        last = end

    result.append(html[last:])
    return ''.join(result)


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
            if any([re.search(r"\b(?<!-)" + re.escape(search) + r"\b(?!-)", class_value) for search in replacements.keys()]):
                if 'manual_nav_template_lines' not in stats:
                    stats['manual_nav_template_lines'] = []
                stats['manual_nav_template_lines'].append(f"{file_path} - Please review manually '{class_value}'")
        else:
            for search, replace in replacements.items():
                # Only replace whole words in class attribute
                pattern = r'\b(?<!-)' + re.escape(search) + r'\b(?!-)'
                class_value, num_replacements = re.subn(pattern, replace, class_value, flags=re.IGNORECASE)
                if num_replacements > 0:
                    logger.debug(
                        'Replaced "%s" with "%s" (%d times) in class="%s"', search, replace, num_replacements, original
                    )
                    stats['replacements'] += num_replacements
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
        pattern = r'\b' + re.escape(search) + r'\b'
        html_string, num_replacements = re.subn(pattern, replace, html_string, flags=re.IGNORECASE)
        if num_replacements > 0:
            logger.debug('Replaced "%s" with "%s" (%d times).', search, replace, num_replacements)
            stats['replacements'] += num_replacements
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
    pattern = re.compile(
        r'<span([^>]*)class="([^"]*\bcaret\b[^"]*)"([^>]*)>(.*?)</span>',
        re.DOTALL | re.IGNORECASE
    )

    def replacer(match):
        before = match.group(1)
        class_attr = match.group(2)
        after = match.group(3)
        inner_html = match.group(4)
        classes = [c for c in class_attr.split() if c != 'caret']
        classes += ['mdi', 'mdi-chevron-down']
        stats['replacements'] += 1
        return f'<span{before}class="{" ".join(classes)}"{after}>{inner_html}</span>'

    return pattern.sub(replacer, html)

def _convert_hover_copy_buttons(html: str, stats: dict) -> str:
    """
    Converts hover copy buttons to the new design (Bootstrap 5).
    """
    # Pattern to match <button ...hover_copy_button...>...</button>
    button_pattern = re.compile(
        r'(<button[^>]*class="[^"]*\bhover_copy_button\b[^"]*"[^>]*>)(.*?)(</button>)',
        re.DOTALL | re.IGNORECASE
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
            if 'aria-hidden=' not in tag:
                tag = tag.replace('<span', '<span aria-hidden="true"', 1)
            return tag
        inner_html = re.sub(
            r'<span([^>]*)class="([^"]*\bmdi\b[^"]*)"([^>]*)>',
            mdi_replacer,
            inner_html
        )

        # Add visually-hidden Copy span if not present
        if not re.search(r'<span[^>]*class="[^"]*\bvisually-hidden\b[^"]*"[^>]*>Copy</span>', inner_html, re.IGNORECASE):
            inner_html += '<span class="visually-hidden">Copy</span>'

        stats['replacements'] += 1
        return f"{open_tag}{inner_html}{close_tag}"

    return button_pattern.sub(button_replacer, html)

def _remove_classes(html: str, classes_to_remove: list[str], stats: dict) -> str:
    """
    Removes each class in classes_to_remove from all class attributes in the HTML string.
    """
    # Build a regex pattern to match any of the classes as a whole word in a class attribute
    pattern = re.compile(
        r'class="([^"]*)"'
    )

    def class_replacer(match):
        class_attr = match.group(1)
        classes = class_attr.split()
        new_classes = [c for c in classes if c not in classes_to_remove]
        removed = len(classes) - len(new_classes)
        if removed > 0:
            stats['replacements'] += removed
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
    html = re.sub(r'\sclass=""', '', html)
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
            if 'breadcrumb-item' not in classes:
                classes.append('breadcrumb-item')
                stats['breadcrumb_items'] += 1
                # Replace the class attribute with the new value
                new_class_attr = f'class="{ " ".join(classes) }"'
                li_tag = re.sub(r'class=(["\'])(.*?)\1', new_class_attr, li_tag, flags=re.IGNORECASE)
        else:
            # Add class attribute with breadcrumb-item
            li_tag = re.sub(r'<li', '<li class="breadcrumb-item"', li_tag, count=1)
            stats['breadcrumb_items'] += 1
        return li_tag

    # Replace all <li ...> tags
    return re.sub(r'<li[^>]*>', li_replacer, html)

def _fix_extra_breadcrumbs_block(html_string: str, stats: dict) -> str:
    """
    Finds {% block extra_breadcrumbs %} blocks and adds 'breadcrumb-item' to <li> tags inside using regex.
    """
    block_pattern = re.compile(
        r'({%\s*block\s+extra_breadcrumbs\s*%})(.*?)({%\s*endblock\s+extra_breadcrumbs\s*%})',
        flags=re.DOTALL | re.IGNORECASE
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
        r'({%\s*block\s+breadcrumbs\s*%})(.*?)({%\s*endblock\s+breadcrumbs\s*%})',
        flags=re.DOTALL | re.IGNORECASE
    )

    def process_match(match):
        block_start_tag = match.group(1)
        block_inner_content = match.group(2)
        block_end_tag = match.group(3)
        new_inner_content = _add_breadcrumb_item_to_li(block_inner_content, stats)
        return f"{block_start_tag}{new_inner_content}{block_end_tag}"

    return block_pattern.sub(process_match, html_string)

# --- Main Conversion Function ---

def convert_bootstrap_classes(html_input: str, file_path: str = None) -> tuple[str, dict]:
    """
    Applies various Bootstrap 3 to 5 conversion rules to the HTML content.
    """
    current_html = html_input # Start with the original HTML

    # Initialize stats
    stats = {
        'replacements': 0,
        'extra_breadcrumbs': 0,
        'breadcrumb_items': 0,
        'nav_items': 0,
        'panel_classes': 0,
        'manual_nav_template_lines': [],
    }

    # --- Stage 1: Apply rules that work directly on the HTML string (simple string/regex replacements) ---
    class_replacements = {
        'pull-left': 'float-start',
        'pull-right': 'float-end',
        'center-block': 'd-block mx-auto',  # Bootstrap 5 uses mx-auto for centering
        'btn-xs': 'btn-sm',
        'btn-lg': 'btn',  # btn-lg is supported in Bootstrap 5 but not meaningful different from btn in Nautobot's theme
        'btn-default': 'btn-secondary',
        'close': 'btn-close',
        'label label-default': 'badge bg-default',  # Bootstrap 5 uses general background classes instead of label-default
        'label label-primary': 'badge bg-primary',
        'label label-success': 'badge bg-success',
        'label label-warning': 'badge bg-warning',
        'label label-danger': 'badge bg-danger',
        'label label-info': 'badge bg-info',
        'label label-transparent': 'badge bg-transparent',
        'text-muted': 'text-secondary',
        'sr-only': 'visually-hidden',  # Bootstrap 5 uses visually-hidden instead of sr-only
        'sr-only-focusable': 'visually-hidden-focusable',  # Bootstrap 5 uses visually-hidden-focusable instead of sr-only-focusable
        'accordion-toggle': 'nb-collapse-toggle',  # Custom class to handle accordion toggles
        'banner-bottom': 'nb-banner-bottom',  # Custom class to handle bottom banners
        'color-block': 'nb-color-block',  # Custom class to handle color blocks
        'editor-container': 'nb-editor-container',  # Custom class to handle editor containers
        'loading': 'nb-loading',  # Custom class to handle loading indicators
        'required': 'nb-required',  # Custom class to handle required fields
        'noprint': 'd-print-none',  # Bootstrap 5 uses d-print-none instead of noprint
        'report-stats': 'nb-report-stats',  # Custom class to handle report stats
        'right-side-panel': 'nb-right-side-panel',  # Custom class to handle right side panels
        'software-image-hierarchy': 'nb-software-image-hierarchy',  # Custom class to handle software image hierarchy
        'tree-hierarchy': 'nb-tree-hierarchy',  # Custom class to handle tree hierarchy
        'tiles': 'nb-tiles',  # Custom class
        'tile': 'nb-tile',  # Custom class
        'tile-description': 'nb-tile-description',  # Custom class
        'tile-footer': 'nb-tile-footer',  # Custom class
        'tile-header': 'nb-tile-header',  # Custom class
        'table-headings': 'nb-table-headings',  # Custom class
        'description': 'nb-description',  # Custom class
        'style-line': 'nb-style-line',  # Custom class
    }
    # Add column offset fixup, e.g. col-sm-offset-4 --> offset-sm-4
    for bkpt in ["xs", "sm", "md", "lg", "xl", "xxl"]:
        for size in range(0, 13):
            class_replacements[f"col-{bkpt}-offset-{size}"] = f"offset-{bkpt}-{size}"

    attribute_replacements = {
        'data-toggle': 'data-bs-toggle',  # Bootstrap 5 uses data-bs-* attributes
        'data-dismiss': 'data-bs-dismiss',  # Bootstrap 5 uses data-bs-* attributes
        'data-target': 'data-bs-target',  # Bootstrap 5 uses data-bs-* attributes
        'data-title': 'data-bs-title',  # Bootstrap 5 uses data-bs-* attributes
        'data-backdrop': 'data-bs-backdrop',  # Bootstrap 5 uses data-bs-* attributes
    }

    current_html = _replace_attributes(current_html, attribute_replacements, stats)
    current_html = _replace_classes(current_html, class_replacements, stats, file_path=file_path)
    current_html = _fix_extra_breadcrumbs_block(current_html, stats)
    current_html = _fix_breadcrumbs_block(current_html, stats)
    current_html = _fix_extra_nav_tabs_block(current_html, stats, file_path=file_path)
    current_html = _fix_breadcrumb_items(current_html, stats)
    current_html = _fix_panel_classes(current_html, stats)
    current_html = _remove_classes(current_html, ['powered-by-nautobot', 'inline-color-block', 'panel-default', "hover_copy"], stats)  # Remove small form/input classes
    current_html = _convert_caret_in_span_to_mdi(current_html, stats)
    current_html = _convert_hover_copy_buttons(current_html, stats)
    current_html = _fix_nav_tabs_items(current_html, stats, file_path=file_path)

    return current_html, stats


# --- File Processing ---

def fix_html_files_in_directory(directory: str, resize=False) -> None:
    """
    Recursively finds all .html files in the given directory, applies convert_bootstrap_classes,
    and overwrites each file with the fixed content. If resize is True, it will only change the
    breakpoints (This should only be done once.).
    """

    totals = {k: 0 for k in ['replacements', 'extra_breadcrumbs', 'breadcrumb_items', 'nav_items', 'panel_classes', 'resizing_xs']}
    # Breakpoints that are not xs do not count as failures in djlint, so we keep a separate counter
    resizing_other = 0

    if os.path.isfile(directory):
        only_filename = os.path.basename(directory)
        directory = os.path.dirname(directory)
    else:
        only_filename = None
    for root, _, files in os.walk(directory):
        for filename in files:
            if only_filename and only_filename != filename:
                continue
            if filename.lower().endswith('.html'):
                file_path = os.path.join(root, filename)
                logger.info("Processing: %s", file_path)
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()

                content = original_content

                if resize:
                    # If resize is True, we only change the breakpoints
                    # This is a one-time operation to adjust the breakpoints.
                    logger.info("Resizing Breakpoints: %s", file_path)

                    # Define the breakpoint mapping
                    breakpoint_map = {
                        'xs': 'sm',
                        'sm': 'md',
                        'md': 'lg',
                        'lg': 'xl',
                        'xl': 'xxl'
                    }

                    resizing_other = 0

                    # Iterate from the highest breakpoint to the lowest
                    for breakpoint in ['xl', 'lg', 'md', 'sm', 'xs']:
                        new_breakpoint = breakpoint_map[breakpoint]
                        # Replace with regex, e.g., col-xs-12 → col-sm-12
                        regex = re.compile(rf'(\bcol-{breakpoint})([a-zA-Z0-9-]*)')
                        def regex_repl(m):
                            nonlocal resizing_other
                            if breakpoint == 'xs':
                                totals['resizing_xs'] += 1
                            else:
                                resizing_other += 1
                            return f'col-{new_breakpoint}{m.group(2)}'
                        content = regex.sub(regex_repl, content)

                fixed_content, stats = convert_bootstrap_classes(content, file_path=file_path)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                logger.info("Fixed: %s", file_path)

                if any([stat for stat in stats.values()]):
                    print(f"→ {os.path.relpath(file_path, directory)}: ", end='')
                    if stats["replacements"]:
                        print(f"{stats['replacements']} class replacements, ", end='')
                    if stats["extra_breadcrumbs"]:
                        print(f"{stats['extra_breadcrumbs']} extra-breadcrumbs, ", end='')
                    if stats["breadcrumb_items"]:
                        print(f"{stats['breadcrumb_items']} breadcrumb-items, ", end='')
                    if stats["nav_items"]:
                        print(f"{stats['nav_items']} nav-items, ", end='')
                    if stats["panel_classes"]:
                        print(f"{stats['panel_classes']} panel replacements, ", end='')
                    print()

                if stats.get('manual_nav_template_lines'):
                    print("  !!! Manual review needed for nav-item fixes at:")
                    for line in stats['manual_nav_template_lines']:
                        print(f"    - {line}")
                for k, v in stats.items():
                    if k in totals:
                        totals[k] += v

    # Global summary
    total_issues = sum(totals.values())
    print("=== Global Summary ===")
    print(f"Total issues fixed: {total_issues}")
    print(f"- Class replacements:          {totals['replacements']}")
    print(f"- Extra-breadcrumb fixes:      {totals['extra_breadcrumbs']}")
    print(f"- <li> in <ol.breadcrumb>:     {totals['breadcrumb_items']}")
    print(f"- <li> in <ul.nav-tabs>:       {totals['nav_items']}")
    print(f"- Panel class replacements:    {totals['panel_classes']}")
    print(f"- Resizing breakpoint xs:      {totals['resizing_xs']}")
    print("-------------------------------------")
    print(f"- Resizing other breakpoints:  {resizing_other}")


def main():
    parser = argparse.ArgumentParser(description="Bootstrap 3 to 5 HTML fixer.")
    parser.add_argument(
        "-r",
        "--resize",
        action="store_true",
        help="Change column breakpoints to be one level higher, such as 'col-xs-*' to 'col-sm-*'",
    )
    parser.add_argument("path", type=str, help='Path to directory in which to recursively fix all .html files.')
    args = parser.parse_args()

    fix_html_files_in_directory(args.path, resize=args.resize)


if __name__ == "__main__":
    main()
