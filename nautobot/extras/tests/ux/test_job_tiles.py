# pylint: skip-file
# The development container does not install Playwright and pytest, so pylint cannot import these modules.
"""UX tests for the actions menu of the Jobs list, in the tiles display and in the list display."""

import re

from conftest import (
    APP_PASSWORD,
    APP_USER,
    check_accessibility,
    login,
    open_nav_item,
    screenshot,
    wait_for_focus_indicator,
)
from playwright.sync_api import expect, Page
import pytest

TILE = ".nb-tiles article.nb-tile"
ACTIONS_BUTTON = ".nb-tile-header .dropdown > button.dropdown-toggle"
# The page script moves an open dropdown menu to the end of the page body, so find it by its "show" class.
OPEN_MENU = ".dropdown-menu.show"
JOB_DETAIL_URL = re.compile(r"/extras/jobs/[0-9a-f-]{36}/$")


def open_jobs(page: Page, display: str):
    """Open the Jobs list from the navigation menu, then select the display with its toggle button."""
    open_nav_item(page, "Jobs", "Jobs")
    expect(page).to_have_url(re.compile(r"/extras/jobs/"))
    page.get_by_role("link", name=display, exact=True).click()
    page.wait_for_load_state("networkidle")


def open_tiles(page: Page):
    open_jobs(page, "Tiles")
    expect(page.locator(TILE).first).to_be_visible()


def test_tiles_actions_button_and_menu_with_all_permissions(new_page):
    """A user with all permissions sees the vertical three-dot actions button and the full actions menu."""
    page = new_page()
    login(page, APP_USER, APP_PASSWORD)
    open_tiles(page)

    tiles = page.locator(TILE)
    first_tile = tiles.first
    screenshot(page, "01-job-tiles")
    screenshot(page, "02-job-tile-header", locator=first_tile.locator(".nb-tile-header"))

    # Each tile has one actions button, and the button shows the vertical three-dot icon.
    tile_count = tiles.count()
    expect(page.locator(f"{TILE} {ACTIONS_BUTTON} .mdi-dots-vertical")).to_have_count(tile_count)
    expect(page.locator(".nb-tiles .mdi-dots-horizontal")).to_have_count(0)

    check_accessibility(page, "01-job-tiles")

    first_tile.locator(ACTIONS_BUTTON).click()
    menu = page.locator(OPEN_MENU)
    expect(menu).to_be_visible()
    expect(menu.locator(".dropdown-item")).to_have_text(["Details", "Change log", "Edit", "Delete"])
    expect(menu.locator("li:has(hr.dropdown-divider) + li")).to_have_text("Delete")
    screenshot(page, "03-job-tile-actions-menu", full_page=False)
    check_accessibility(page, "03-job-tile-actions-menu")

    menu.get_by_role("link", name="Details").click()
    expect(page).to_have_url(JOB_DETAIL_URL)
    page.errors.check()


def test_tiles_actions_menu_with_keyboard(new_page):
    """A keyboard user can move to the actions button, open the menu, and open the Job details."""
    page = new_page()
    login(page, APP_USER, APP_PASSWORD)
    open_tiles(page)

    button = page.locator(f"{TILE} {ACTIONS_BUTTON}").first
    handle = button.element_handle()
    for _ in range(300):
        if page.evaluate("(el) => document.activeElement === el", handle):
            break
        page.keyboard.press("Tab")
    expect(button).to_be_focused()
    expect(button).to_be_in_viewport()
    if not button.evaluate("(el) => el.matches(':focus-visible')"):
        pytest.fail("The focused actions button does not show a visible focus indicator.")
    wait_for_focus_indicator(page, button)
    screenshot(page, "04-keyboard-focus-actions-button", locator=button.locator("xpath=ancestor::header"))

    page.keyboard.press("Enter")
    menu = page.locator(OPEN_MENU)
    expect(menu).to_be_visible()
    # The arrow keys move the focus into an open Bootstrap dropdown menu.
    page.keyboard.press("ArrowDown")
    details = menu.get_by_role("link", name="Details")
    expect(details).to_be_focused()
    wait_for_focus_indicator(page, details)
    screenshot(page, "05-keyboard-focus-details", full_page=False)
    page.keyboard.press("Enter")
    expect(page).to_have_url(JOB_DETAIL_URL)
    page.errors.check()


def test_list_display_actions_unchanged(new_page):
    """The list display of the Jobs still shows the table with its own actions buttons."""
    page = new_page()
    login(page, APP_USER, APP_PASSWORD)
    open_jobs(page, "List")

    expect(page.locator(".nb-tiles")).to_have_count(0)
    table = page.locator("table").first
    expect(table).to_be_visible()
    expect(table.locator(".mdi-dots-horizontal")).to_have_count(0)
    screenshot(page, "06-job-list")
    check_accessibility(page, "06-job-list")
    page.errors.check()


def test_tiles_actions_menu_with_view_permission_only(new_page, view_only_user):
    """A user who can only view Jobs sees only Details and Change log in the actions menu."""
    username, password = view_only_user
    page = new_page()
    login(page, username, password)
    open_tiles(page)

    first_tile = page.locator(TILE).first
    expect(first_tile.locator(f"{ACTIONS_BUTTON} .mdi-dots-vertical")).to_have_count(1)
    first_tile.locator(ACTIONS_BUTTON).click()
    menu = page.locator(OPEN_MENU)
    expect(menu).to_be_visible()
    expect(menu.locator(".dropdown-item")).to_have_text(["Details", "Change log"])
    expect(menu.locator("hr.dropdown-divider")).to_have_count(0)
    screenshot(page, "07-job-tile-actions-menu-view-only", full_page=False)
    check_accessibility(page, "07-job-tile-actions-menu-view-only")
    page.errors.check()
