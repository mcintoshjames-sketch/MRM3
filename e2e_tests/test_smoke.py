import pytest
from playwright.sync_api import Page, expect


def test_dashboard_loads(authenticated_page: Page):
    """
    Verify that the dashboard loads for an authenticated user.
    """
    # The authenticated_page fixture has already logged us in and navigated to BASE_URL

    # Check if we are on the dashboard or home page
    # Adjust the URL pattern as needed (e.g., /dashboard)
    expect(authenticated_page).to_have_url(lambda url: "/login" not in url)

    # Check for a common element, e.g., the navigation sidebar or a header
    # expect(authenticated_page.get_by_role("navigation")).to_be_visible()

    # Example: Check if "Models" link is present (based on CLAUDE.md description)
    # expect(authenticated_page.get_by_text("Models")).to_be_visible()


def test_models_page_access(authenticated_page: Page):
    """
    Verify access to the Models page.
    """
    authenticated_page.goto("/models")

    # Verify we are on the models page
    expect(authenticated_page).to_have_url(lambda url: "/models" in url)

    # Verify the table or header is visible
    # expect(authenticated_page.get_by_role("heading", name="Models")).to_be_visible()
