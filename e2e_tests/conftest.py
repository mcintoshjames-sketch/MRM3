import pytest
import os
from playwright.sync_api import Page, expect

# Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:5174")
API_URL = os.getenv("API_URL", "http://localhost:8001")

# Default credentials from CLAUDE.md
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "user123"


@pytest.fixture(scope="session")
def api_request_context(playwright):
    """
    Creates a Playwright API request context.
    This allows making HTTP requests directly to the backend (e.g. for setup/teardown).
    """
    request_context = playwright.request.new_context(base_url=API_URL)
    yield request_context
    request_context.dispose()


@pytest.fixture(scope="session")
def admin_token(api_request_context):
    """
    Logs in as admin and returns the JWT token.
    """
    response = api_request_context.post("/auth/login", data={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })

    if not response.ok:
        raise RuntimeError(
            f"Failed to login as admin: {response.status} {response.text()}")

    data = response.json()
    return data["access_token"]


@pytest.fixture
def authenticated_page(page: Page, admin_token):
    """
    Fixture that provides a Playwright Page instance that is already logged in.
    It injects the JWT token into localStorage.
    """
    # 1. Navigate to the app's base URL.
    #    This is necessary to set localStorage for the correct origin.
    #    We might get redirected to /login, which is fine.
    page.goto(BASE_URL)

    # 2. Inject the token into localStorage
    #    The key 'token' matches what is used in src/contexts/AuthContext.tsx
    page.evaluate(f"localStorage.setItem('token', '{admin_token}')")

    # 3. Reload the page to trigger the AuthProvider's useEffect
    #    which reads the token and fetches the user.
    page.reload()

    # 4. Wait for a sign that we are logged in.
    #    For example, the "Dashboard" link or text should be visible.
    #    Adjust this selector based on your actual UI.
    #    Here we wait for something that indicates we are NOT on the login page.
    try:
        # Assuming the dashboard has a heading or link named "Dashboard"
        # or simply wait for the URL to not be /login
        expect(page).not_to_have_url(f"{BASE_URL}/login", timeout=10000)
    except AssertionError:
        print(
            "Warning: Still on login page after token injection. Check AuthContext logic.")

    return page


@pytest.fixture(scope="session")
def db_state_check(api_request_context):
    """
    Optional: Check if the database is reachable and has basic data.
    """
    response = api_request_context.get(
        "/health")  # Assuming a health endpoint exists
    # If no health endpoint, try a simple fetch
    if not response.ok:
        # Try fetching users as a check
        response = api_request_context.get("/auth/users")

    if not response.ok and response.status != 401:
        print(
            f"Warning: Database or API might be down. Status: {response.status}")
