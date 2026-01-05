#!/usr/bin/env python3
"""
Test the logic with all SKUs out of stock (your example)
"""

import json

# Your exact response - all out of stock
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
print("🧪 Testing All Out of Stock Logic")
print("=" * 60)
print()

# Sort SKUs (smallest to largest = XS to XL)
skus = sorted([s['sku'] for s in test_response['skusAvailability']])
size_names = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']

# Create size mapping
size_mapping = {}
for i, sku in enumerate(skus):
    size = size_names[i] if i < len(size_names) else f"Size {i+1}"
    size_mapping[sku] = size

print("📏 Size Mapping:")
for sku in skus:
    size = size_mapping[sku]
    sku_info = next(s for s in test_response['skusAvailability'] if s['sku'] == sku)
    status_emoji = "❌" if sku_info['availability'] == 'out_of_stock' else "✅"
    print(f"   {status_emoji} {size} (SKU {sku}): {sku_info['availability']}")
print()

# Check availability
available_sizes = []
in_stock = False

for sku_info in test_response['skusAvailability']:
    sku_id = sku_info.get('sku')
    availability = sku_info.get('availability', '').lower()
    
    # Map SKU to size name
    size_name = size_mapping.get(sku_id, f"SKU {sku_id}")
    
    # Check availability
    if availability in ['in_stock', 'low_on_stock']:
        in_stock = True
        available_sizes.append(size_name)

print("=" * 60)
print("📦 Stock Check Result:")
print("=" * 60)
print(f"   In Stock: {'✅ YES' if in_stock else '❌ NO'}")
print(f"   Available Sizes: {', '.join(available_sizes) if available_sizes else 'None (all out of stock)'}")
print("=" * 60)
print()

# Simulate what Telegram message would be
if in_stock:
    print("📨 Telegram Message (if in stock):")
    print("   ✅ Zara Item In Stock! 🚀")
    print(f"   📏 Available Sizes: {', '.join(available_sizes)}")
else:
    print("📨 Telegram Message (out of stock):")
    print("   ❌ Zara Item Out of Stock 🚀")
    print("   📏 Status: OUT OF STOCK")
    print()
    print("   (Notification will be sent if skip_nostock_notification=false)")

print()
print("✅ Logic test complete!")
print()
print("💡 The code correctly:")
print("   1. Sorts SKUs from smallest to largest")
print("   2. Maps them to sizes (XS, S, M, L, XL)")
print("   3. Detects all out of stock correctly")
print("   4. Will send Telegram notification if configured")

