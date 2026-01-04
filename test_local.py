#!/usr/bin/env python3
"""
Simple local test script for Zara Stock Checker
Run: python3 test_local.py
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Test URL
TEST_URL = "https://www.zara.com/uk/en/wool-double-breasted-coat-p08475319.html"

def test_browserless():
    """Test with Browserless if token/URL is set."""
    if not (os.environ.get("BROWSERLESS_TOKEN") or os.environ.get("BROWSERLESS_URL")):
        print("ℹ️  BROWSERLESS_TOKEN or BROWSERLESS_URL not set, will use local Selenium")
        return False
    
    print("🧪 Testing with Browserless...")
    try:
        from zara_stock_checker_browser import ZaraStockCheckerBrowser
        checker = ZaraStockCheckerBrowser(verbose=True, headless=True)
        
        print(f"🌐 Fetching: {TEST_URL}")
        html = checker.fetch_product_page(TEST_URL)
        
        # Check if we got blocked - real Zara pages are tens of thousands of chars, not 336
        blocked = (not html) or ("Access Denied" in html) or (len(html) < 2000)
        if blocked:
            print(f"❌ Blocked / junk HTML ({len(html) if html else 0} chars)")
            if html:
                print(f"\n📄 HTML content:")
                print("-" * 80)
                print(html)
                print("-" * 80)
            return False
        
        print(f"✅ Success! Got {len(html)} chars of HTML (looks like real content)")
        
        # Test parsing
        stock_info = checker.check_stock(TEST_URL)
        print(f"\n📦 Stock Info:")
        print(f"  Name: {stock_info.get('name', 'N/A')}")
        print(f"  Price: {stock_info.get('price', 'N/A')}")
        print(f"  In Stock: {stock_info.get('in_stock', False)}")
        print(f"  Sizes: {', '.join(stock_info.get('available_sizes', []))}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_local_selenium():
    """Test with local Selenium/undetected-chromedriver."""
    print("🧪 Testing with local Selenium...")
    try:
        from zara_stock_checker_browser import ZaraStockCheckerBrowser
        checker = ZaraStockCheckerBrowser(verbose=True, headless=False)  # Show browser for debugging
        
        print(f"🌐 Fetching: {TEST_URL}")
        html = checker.fetch_product_page(TEST_URL)
        
        if html and len(html) > 100:
            print(f"✅ Success! Got {len(html)} chars of HTML")
            
            # Test parsing
            stock_info = checker.check_stock(TEST_URL)
            print(f"\n📦 Stock Info:")
            print(f"  Name: {stock_info.get('name', 'N/A')}")
            print(f"  Price: {stock_info.get('price', 'N/A')}")
            print(f"  In Stock: {stock_info.get('in_stock', False)}")
            print(f"  Sizes: {', '.join(stock_info.get('available_sizes', []))}")
            
            # Cleanup
            checker.cleanup()
            return True
        else:
            print(f"❌ Failed: Got empty or too short HTML ({len(html) if html else 0} chars)")
            checker.cleanup()
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Zara Stock Checker - Local Test")
    print("=" * 60)
    print()
    
    # Check if Browserless token/URL is set
    if os.environ.get("BROWSERLESS_TOKEN") or os.environ.get("BROWSERLESS_URL"):
        success = test_browserless()
    else:
        print("ℹ️  BROWSERLESS_TOKEN or BROWSERLESS_URL not set, testing with local Selenium")
        print("   (Set BROWSERLESS_TOKEN or BROWSERLESS_URL to test Browserless)")
        print()
        success = test_local_selenium()
    
    print()
    print("=" * 60)
    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed")
    print("=" * 60)
    
    sys.exit(0 if success else 1)

