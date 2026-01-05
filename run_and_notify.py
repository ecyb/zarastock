#!/usr/bin/env python3
"""
Run stock check and send Telegram notification
"""

import os
import sys
from dotenv import load_dotenv

# Try to load .env (may fail due to permissions, that's OK)
try:
    load_dotenv()
except:
    pass

# Use product page URL - will extract product ID and call API
PRODUCT_PAGE_URL = "https://www.zara.com/uk/en/wool-double-breasted-coat-p08475319.html"

# Direct API URL (for reference - product ID: 483276547, store: 10706)
API_URL = "https://www.zara.com/itxrest/1/catalog/store/10706/product/id/483276547/availability"

print("=" * 60)
print("🚀 Running Stock Check & Sending Telegram Notification")
print("=" * 60)
print()

try:
    from zara_stock_checker import ZaraStockChecker
    
    checker = ZaraStockChecker(verbose=True)
    
    # Check Telegram config
    telegram_config = checker.config.get('telegram', {})
    bot_token = telegram_config.get('bot_token', '') or os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('api_key')
    chat_ids = telegram_config.get('chat_ids', [])
    enabled = telegram_config.get('enabled', False)
    
    print("📱 Telegram Configuration:")
    print(f"   Enabled: {enabled}")
    print(f"   Bot Token: {'✅ SET' if bot_token and bot_token != 'YOUR_BOT_TOKEN' else '❌ NOT SET'}")
    print(f"   Chat IDs: {chat_ids}")
    print()
    
    if not bot_token or bot_token == 'YOUR_BOT_TOKEN':
        print("⚠️  Telegram bot token not configured!")
        print()
        print("To enable Telegram notifications:")
        print("1. Get bot token from @BotFather on Telegram")
        print("2. Set in config.json: \"bot_token\": \"your_token\"")
        print("   OR set environment variable: TELEGRAM_BOT_TOKEN=your_token")
        print()
        print("Continuing with stock check (no notification will be sent)...")
        print()
    else:
        # Update config with token from env if needed
        if not telegram_config.get('bot_token') or telegram_config.get('bot_token') == 'YOUR_BOT_TOKEN':
            checker.config['telegram']['bot_token'] = bot_token
    
    # Check stock using product page URL (will extract product ID and call API)
    print("1️⃣  Checking stock...")
    print(f"   Product Page: {PRODUCT_PAGE_URL}")
    print(f"   Expected API: {API_URL}")
    print()
    
    # Try product page URL first (will extract product ID and call API)
    stock_info = checker.check_stock(PRODUCT_PAGE_URL)
    
    # If that fails, try direct API URL
    if stock_info.get('error') or (not stock_info.get('name') and not stock_info.get('in_stock') is not None):
        print("   ⚠️  Product page check failed, trying direct API URL...")
        print()
        stock_info = checker.check_stock(API_URL)
    
    # Extract product name from URL if missing
    if not stock_info.get('name') or stock_info.get('name') == 'Unknown Product':
        print("   📝 Extracting product name from URL...")
        try:
            import re
            # Extract from product page URL slug
            # Format: https://www.zara.com/uk/en/wool-double-breasted-coat-p08475319.html
            # Extract: wool-double-breasted-coat
            if PRODUCT_PAGE_URL:
                url_match = re.search(r'/([^/]+)-p\d+\.html', PRODUCT_PAGE_URL)
                if url_match:
                    slug = url_match.group(1)
                    # Convert slug to title case: wool-double-breasted-coat -> Wool Double Breasted Coat
                    product_name = slug.replace('-', ' ').title()
                    stock_info['name'] = product_name
                    print(f"   ✅ Product name: {product_name}")
                else:
                    # Fallback: use last part of URL
                    url_parts = PRODUCT_PAGE_URL.split('/')
                    if len(url_parts) > 0:
                        last_part = url_parts[-1].replace('.html', '').split('-p')[0].replace('-', ' ').title()
                        stock_info['name'] = last_part
                        print(f"   ✅ Product name (from URL): {last_part}")
        except Exception as e:
            print(f"   ⚠️  Could not extract product name: {e}")
    
    # Set product page URL for Telegram "View Product" link
    if PRODUCT_PAGE_URL and '/itxrest/' not in PRODUCT_PAGE_URL:
        stock_info['product_page_url'] = PRODUCT_PAGE_URL
        stock_info['original_url'] = PRODUCT_PAGE_URL
    
    print()
    print("=" * 60)
    print("📦 Stock Check Result:")
    print("=" * 60)
    print(f"   Name: {stock_info.get('name', 'N/A')}")
    print(f"   Price: {stock_info.get('price', 'N/A')}")
    print(f"   In Stock: {'✅ YES' if stock_info.get('in_stock') else '❌ NO'}")
    print(f"   Available Sizes: {', '.join(stock_info.get('available_sizes', []))}")
    print(f"   Method: {stock_info.get('method', 'html')}")
    print("=" * 60)
    print()
    
    # Send notification if Telegram is configured
    if bot_token and bot_token != 'YOUR_BOT_TOKEN' and chat_ids:
        print("2️⃣  Sending Telegram notification...")
        try:
            checker.send_notification(stock_info)
            print("   ✅ Notification sent successfully!")
        except Exception as e:
            print(f"   ❌ Error sending notification: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("2️⃣  Skipping Telegram notification (not configured)")
        if not bot_token or bot_token == 'YOUR_BOT_TOKEN':
            print("   💡 Set bot token to enable notifications")
        elif not chat_ids:
            print("   💡 Add chat_ids to config.json")
    
    print()
    print("=" * 60)
    print("✅ Done!")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

