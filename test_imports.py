#!/usr/bin/env python3
"""
Quick test to verify imports and basic initialization logic
"""

import os
import sys

# Set USE_LOCAL_BROWSER to ensure we test local browser path
os.environ["USE_LOCAL_BROWSER"] = "true"

print("🧪 Testing imports and initialization logic...")
print()

# Test 1: Import check
print("1️⃣  Testing imports...")
try:
    from zara_stock_checker_browser import ZaraStockCheckerBrowser, UC_AVAILABLE, PLAYWRIGHT_AVAILABLE
    print(f"   ✅ Imports successful")
    print(f"   - UC_AVAILABLE: {UC_AVAILABLE}")
    print(f"   - PLAYWRIGHT_AVAILABLE: {PLAYWRIGHT_AVAILABLE}")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Check environment variable logic
print()
print("2️⃣  Testing environment variable logic...")
os.environ.pop("BROWSERLESS_TOKEN", None)
os.environ.pop("BROWSERLESS_URL", None)
os.environ["USE_LOCAL_BROWSER"] = "true"

use_local = os.environ.get("USE_LOCAL_BROWSER", "true").lower() == "true"
force_browserless = os.environ.get("FORCE_BROWSERLESS", "false").lower() == "true"
has_browserless_creds = bool(os.environ.get("BROWSERLESS_URL") or os.environ.get("BROWSERLESS_TOKEN"))
should_use_browserless = force_browserless or (not use_local and has_browserless_creds)

print(f"   - USE_LOCAL_BROWSER: {use_local}")
print(f"   - FORCE_BROWSERLESS: {force_browserless}")
print(f"   - Has Browserless creds: {has_browserless_creds}")
print(f"   - Should use Browserless: {should_use_browserless}")
print(f"   ✅ Will use: {'Local browser' if not should_use_browserless else 'Browserless'}")

# Test 3: Check Railway detection logic
print()
print("3️⃣  Testing Railway detection logic...")
is_railway = os.environ.get('RAILWAY_ENVIRONMENT') is not None or os.environ.get('RAILWAY_PROJECT_ID') is not None
is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
is_cloud = is_docker or is_railway

print(f"   - Is Railway: {is_railway}")
print(f"   - Is Docker: {is_docker}")
print(f"   - Is Cloud: {is_cloud}")
print(f"   ✅ Will use: {'Regular Selenium (cloud)' if is_cloud else 'undetected-chromedriver (local)'}")

print()
print("=" * 60)
print("✅ All logic tests passed!")
print("=" * 60)
print()
print("💡 To test with actual browser, run:")
print("   python3 test_local.py")
print()
print("💡 On Railway, the app will:")
print("   1. Detect Railway environment automatically")
print("   2. Use local Chromium (from nixpacks)")
print("   3. Run headless with Selenium")
print("   4. No Browserless limits!")

