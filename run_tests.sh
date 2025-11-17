#!/bin/bash

# Run all tests for MRM Inv 3
set -e

echo "========================================="
echo "Running API Tests (Python)"
echo "========================================="
cd api && python3 -m pytest
echo ""

echo "========================================="
echo "Running Web Tests (pnpm)"
echo "========================================="
cd ../web && pnpm test:run
echo ""

echo "========================================="
echo "All tests passed! ✓"
echo "========================================="
