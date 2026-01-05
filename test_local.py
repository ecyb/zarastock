#!/usr/bin/env python3
"""
Simple local test script for Zara Stock Checker
Run: python3 test_local.py
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file (optional - may fail due to permissions)
try:
    load_dotenv()
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")
    print("   Continuing without .env file...")

# Test URL
TEST_URL = "https://www.zara.com/uk/en/wool-double-breasted-coat-p08475319.html"

def test_browserless():
    """Test with Browserless if explicitly forced."""
    # Force Browserless by setting FORCE_BROWSERLESS
    if not (os.environ.get("BROWSERLESS_TOKEN") or os.environ.get("BROWSERLESS_URL")):
        print("ℹ️  BROWSERLESS_TOKEN or BROWSERLESS_URL not set, will use local browser")
        return False
    
    # Temporarily force Browserless for this test
    original_force = os.environ.get("FORCE_BROWSERLESS")
    os.environ["FORCE_BROWSERLESS"] = "true"
    
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
    finally:
        # Restore original FORCE_BROWSERLESS setting
        if original_force is None:
            os.environ.pop("FORCE_BROWSERLESS", None)
        else:
            os.environ["FORCE_BROWSERLESS"] = original_force

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
    
    # Test with local browser by default (avoids Browserless limits)
    # Only test Browserless if explicitly requested
    use_browserless = os.environ.get("FORCE_BROWSERLESS", "false").lower() == "true"
    
    if use_browserless and (os.environ.get("BROWSERLESS_TOKEN") or os.environ.get("BROWSERLESS_URL")):
        print("ℹ️  FORCE_BROWSERLESS=true, testing with Browserless")
        print()
        success = test_browserless()
    else:
        print("ℹ️  Testing with local browser (default - no limits!)")
        if os.environ.get("BROWSERLESS_TOKEN") or os.environ.get("BROWSERLESS_URL"):
            print("   (Browserless token found but not used. Set FORCE_BROWSERLESS=true to use it)")
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

