#!/usr/bin/env python3
import requests
import json

# Login
login_resp = requests.post(
    "http://localhost:8001/auth/login",
    json={"email": "admin@example.com", "password": "admin123"}
)
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get taxonomies
taxonomies_resp = requests.get("http://localhost:8001/taxonomies/", headers=headers)
taxonomies = taxonomies_resp.json()

print("=== Taxonomies ===")
for tax in taxonomies:
    print(f"\n{tax['name']} (ID: {tax['taxonomy_id']})")

    # Get values for this taxonomy
    values_resp = requests.get(
        f"http://localhost:8001/taxonomies/{tax['taxonomy_id']}/values",
        headers=headers
    )
    values = values_resp.json()

    for val in values:
        print(f"  - {val['code']}: {val['label']} (ID: {val['value_id']}, Active: {val['is_active']})")

# Check specifically for Validation Type and Validation Priority
print("\n=== Validation-related Taxonomies ===")
validation_taxonomies = [t for t in taxonomies if 'Validation' in t['name']]

for tax in validation_taxonomies:
    print(f"\n{tax['name']} (ID: {tax['taxonomy_id']})")
    values_resp = requests.get(
        f"http://localhost:8001/taxonomies/{tax['taxonomy_id']}/values",
        headers=headers
    )
    values = values_resp.json()

    # Check for TARGETED and INTERIM codes
    if tax['name'] == 'Validation Type':
        targeted = [v for v in values if v['code'] == 'TARGETED']
        interim = [v for v in values if v['code'] == 'INTERIM']
        print(f"  TARGETED found: {len(targeted) > 0}")
        print(f"  INTERIM found: {len(interim) > 0}")

    if tax['name'] == 'Validation Priority':
        priority_2 = [v for v in values if v['code'] == '2']
        priority_3 = [v for v in values if v['code'] == '3']
        print(f"  Priority '2' found: {len(priority_2) > 0}")
        print(f"  Priority '3' found: {len(priority_3) > 0}")
