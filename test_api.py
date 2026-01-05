#!/usr/bin/env python3
"""
Test the new API-based stock checker (no browser needed!)
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file (optional)
try:
    load_dotenv()
except:
    pass

# Test URLs
TEST_PRODUCT_URL = "https://www.zara.com/uk/en/wool-double-breasted-coat-p08475319.html"
TEST_API_URL = "https://www.zara.com/itxrest/1/catalog/store/10706/product/id/483276547/availability"

def test_api_approach():
    """Test the API-based stock checking."""
    print("=" * 60)
    print("🧪 Testing API-based Stock Checker (No Browser!)")
    print("=" * 60)
    print()
    
    try:
        from zara_stock_checker import ZaraStockChecker
        checker = ZaraStockChecker(verbose=True)
        
        # Test 1: Product page URL
        print("1️⃣  Testing with product page URL...")
        print(f"   URL: {TEST_PRODUCT_URL}")
        print()
        
        stock_info = checker.check_stock(TEST_PRODUCT_URL)
        
        print(f"\n📦 Stock Info:")
        print(f"   Name: {stock_info.get('name', 'N/A')}")
        print(f"   Price: {stock_info.get('price', 'N/A')}")
        print(f"   In Stock: {stock_info.get('in_stock', False)}")
        print(f"   Available Sizes: {', '.join(stock_info.get('available_sizes', []))}")
        print(f"   Method: {stock_info.get('method', 'html')}")
        if stock_info.get('error'):
            print(f"   Error: {stock_info.get('error')}")
        
        print()
        print("=" * 60)
        
        # Test 2: Direct API URL
        print("\n2️⃣  Testing with direct API URL...")
        print(f"   URL: {TEST_API_URL}")
        print()
        
        stock_info2 = checker.check_stock(TEST_API_URL)
        
        print(f"\n📦 Stock Info:")
        print(f"   Name: {stock_info2.get('name', 'N/A')}")
        print(f"   Price: {stock_info2.get('price', 'N/A')}")
        print(f"   In Stock: {stock_info2.get('in_stock', False)}")
        print(f"   Available Sizes: {', '.join(stock_info2.get('available_sizes', []))}")
        print(f"   Method: {stock_info2.get('method', 'html')}")
        if stock_info2.get('error'):
            print(f"   Error: {stock_info2.get('error')}")
        
        print()
        print("=" * 60)
        print("✅ Test completed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_approach()
    sys.exit(0 if success else 1)

