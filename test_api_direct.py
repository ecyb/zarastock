#!/usr/bin/env python3
"""
Test with the exact API endpoint you provided
"""

import json
from zara_stock_checker import ZaraStockChecker

# Your exact API URL
API_URL = "https://www.zara.com/itxrest/1/catalog/store/10706/product/id/483276547/availability"

print("=" * 60)
print("🧪 Testing with your exact API endpoint")
print("=" * 60)
print(f"\nURL: {API_URL}\n")

checker = ZaraStockChecker(verbose=True)
stock_info = checker.check_stock(API_URL)

print("\n" + "=" * 60)
print("📦 RESULT:")
print("=" * 60)
print(json.dumps(stock_info, indent=2))
print("=" * 60)

# Show the size mapping logic
print("\n💡 Size Mapping Logic:")
print("   SKUs are sorted by ID (smallest to largest)")
print("   Smallest SKU = XS, Largest SKU = XL")
print("   Example: 495714666 (smallest) = XS, 495714676 (largest) = XL")

