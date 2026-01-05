#!/usr/bin/env python3
"""
Test with the specific API response the user provided
"""

import json
from zara_stock_checker import ZaraStockChecker

# The exact API URL and response you provided
API_URL = "https://www.zara.com/itxrest/1/catalog/store/10706/product/id/483276547/availability"
PRODUCT_PAGE_URL = "https://www.zara.com/uk/en/wool-double-breasted-coat-p08475319.html"

# Your exact response
test_response = {
    "skusAvailability": [
        {"sku": 483272260, "availability": "out_of_stock"},
        {"sku": 483272258, "availability": "out_of_stock"},
        {"sku": 483272259, "availability": "out_of_stock"},
        {"sku": 483272256, "availability": "out_of_stock"},
        {"sku": 483272257, "availability": "out_of_stock"}
    ]
}

print("=" * 60)
print("🧪 Testing with Your Exact API Response")
print("=" * 60)
print()
print("📡 API URL:", API_URL)
print()
print("📦 API Response:")
print(json.dumps(test_response, indent=2))
print()

# Analyze the response
skus = sorted([s['sku'] for s in test_response['skusAvailability']])
print("📊 Analysis:")
print(f"   Total SKUs: {len(skus)}")
print(f"   SKU IDs (sorted): {skus}")
print(f"   Smallest SKU: {skus[0]} (should be XS)")
print(f"   Largest SKU: {skus[-1]} (should be XL)")
print()

# Check availability
in_stock_count = sum(1 for s in test_response['skusAvailability'] if s['availability'] in ['in_stock', 'low_on_stock'])
out_of_stock_count = sum(1 for s in test_response['skusAvailability'] if s['availability'] == 'out_of_stock')

print("📈 Stock Status:")
print(f"   In Stock: {in_stock_count}")
print(f"   Out of Stock: {out_of_stock_count}")
print(f"   Overall: {'❌ OUT OF STOCK' if in_stock_count == 0 else '✅ IN STOCK'}")
print()

# Test with actual checker
print("=" * 60)
print("🚀 Running Actual Check")
print("=" * 60)
print()

checker = ZaraStockChecker(verbose=True)
stock_info = checker.check_stock(API_URL)

# Extract product name if needed
if not stock_info.get('name') or stock_info.get('name') == 'Unknown Product':
    import re
    if PRODUCT_PAGE_URL:
        url_match = re.search(r'/([^/]+)-p\d+\.html', PRODUCT_PAGE_URL)
        if url_match:
            slug = url_match.group(1)
            product_name = slug.replace('-', ' ').title()
            stock_info['name'] = product_name

print()
print("=" * 60)
print("📦 Final Result:")
print("=" * 60)
print(f"   Name: {stock_info.get('name', 'N/A')}")
print(f"   In Stock: {'✅ YES' if stock_info.get('in_stock') else '❌ NO'}")
print(f"   Available Sizes: {', '.join(stock_info.get('available_sizes', [])) if stock_info.get('available_sizes') else 'None'}")
print(f"   Method: {stock_info.get('method', 'N/A')}")
print("=" * 60)
print()

# Show size mapping
if stock_info.get('available_sizes'):
    print("✅ Sizes in stock:", ', '.join(stock_info.get('available_sizes', [])))
else:
    print("❌ No sizes in stock")
    
    # Show what sizes would be mapped
    print()
    print("📏 Size Mapping (for reference):")
    size_names = ['XS', 'S', 'M', 'L', 'XL']
    for i, sku in enumerate(skus):
        size = size_names[i] if i < len(size_names) else f"Size {i+1}"
        status = "❌" if test_response['skusAvailability'][i]['availability'] == 'out_of_stock' else "✅"
        print(f"   {status} {size} (SKU {sku}): {test_response['skusAvailability'][i]['availability']}")

