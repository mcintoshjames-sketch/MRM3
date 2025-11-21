#!/usr/bin/env python3
"""
End-to-end test to verify Emily can see the revalidation banner on model 39.

This script tests the exact scenario that broke:
1. Login as Emily
2. Call all four Promise.all endpoints
3. Verify revalidation status shows overdue
4. Verify banner trigger conditions are met

Run with: docker compose exec api python test_emily_banner.py
"""
import requests
import sys

BASE_URL = "http://localhost:8001"


def test_emily_banner():
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  Emily Banner Regression Test - Model 39                      ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()

    # Step 1: Login as Emily
    print("1. Logging in as Emily Davis...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "emily.davis@contoso.com", "password": "emily123"}
    )

    if login_response.status_code != 200:
        print(f"  ✗ Login failed: HTTP {login_response.status_code}")
        return False

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  ✓ Login successful")
    print()

    # Step 2: Test all four Promise.all endpoints
    print("2. Testing Promise.all endpoints for model 39...")

    endpoints = [
        ("/validations/?model_id=39", "Legacy validations"),
        ("/validation-workflow/requests/?model_id=39", "Validation requests"),
        ("/models/39/versions", "Model versions"),
        ("/models/39/revalidation-status", "Revalidation status")
    ]

    all_passed = True
    revalidation_data = None

    for endpoint, name in endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        status = response.status_code

        if status == 200:
            print(f"  ✓ {name}: HTTP {status}")
            if "revalidation-status" in endpoint:
                revalidation_data = response.json()
        else:
            print(f"  ✗ {name}: HTTP {status}")
            print(f"    Error: {response.text}")
            all_passed = False

    if not all_passed:
        print()
        print("✗ FAILED: Some endpoints returned errors")
        print("  This will cause Promise.all to fail and the banner to disappear!")
        return False

    print()
    print("3. Verifying revalidation status data...")

    if not revalidation_data:
        print("  ✗ No revalidation data received")
        return False

    print(f"  Model: {revalidation_data.get('model_name')}")
    print(f"  Owner: {revalidation_data.get('model_owner')}")
    print(f"  Status: {revalidation_data.get('status')}")
    print(f"  Days until validation due: {revalidation_data.get('days_until_validation_due')}")
    print(f"  Active request ID: {revalidation_data.get('active_request_id')}")
    print()

    # Step 3: Verify banner trigger conditions
    print("4. Checking banner trigger conditions...")

    status = revalidation_data.get("status", "")
    days_until_due = revalidation_data.get("days_until_validation_due")

    # RED banner triggers when:
    # - status contains "Overdue" OR
    # - days_until_validation_due < 0
    has_overdue_status = "Overdue" in status
    has_negative_days = days_until_due is not None and days_until_due < 0

    print(f"  Status contains 'Overdue': {has_overdue_status}")
    print(f"  Days until due < 0: {has_negative_days} ({days_until_due} days)")
    print()

    if has_overdue_status or has_negative_days:
        print("✓ PASSED: Banner should display!")
        print()
        print("Expected banner:")
        print("┌────────────────────────────────────────────────────────────┐")
        print("│ 🔴 Revalidation Overdue                                    │")
        print("│                                                            │")
        print(f"│ This model is {abs(days_until_due)} days overdue for revalidation.    │")
        print("│ Validation was due on 2025-01-13.                         │")
        print("│                                                            │")
        print("│ → View active project (Request #31)                       │")
        print("└────────────────────────────────────────────────────────────┘")
        return True
    else:
        print("✗ FAILED: Banner trigger conditions not met!")
        return False


if __name__ == "__main__":
    success = test_emily_banner()
    sys.exit(0 if success else 1)
