#!/usr/bin/env python3
"""
Test the full flow: API check -> Telegram notification
"""

import os
import json
from dotenv import load_dotenv

try:
    load_dotenv()
except:
    pass

# Test with the API endpoint you provided
API_URL = "https://www.zara.com/itxrest/1/catalog/store/10706/product/id/483276547/availability"

print("=" * 60)
print("🧪 Full Flow Test: API Check + Telegram")
print("=" * 60)
print()

try:
    from zara_stock_checker import ZaraStockChecker
    
    checker = ZaraStockChecker(verbose=True)
    
    print("1️⃣  Checking stock via API...")
    print(f"   URL: {API_URL}")
    print()
    
    stock_info = checker.check_stock(API_URL)
    
    print("\n" + "=" * 60)
    print("📦 Stock Check Result:")
    print("=" * 60)
    print(json.dumps(stock_info, indent=2))
    print("=" * 60)
    print()
    
    # Check Telegram config
    telegram_enabled = checker.config.get('telegram', {}).get('enabled', False)
    bot_token = checker.config.get('telegram', {}).get('bot_token', '')
    chat_ids = checker.config.get('telegram', {}).get('chat_ids', [])
    
    print("\n2️⃣  Telegram Configuration:")
    print(f"   Enabled: {telegram_enabled}")
    print(f"   Bot Token: {'✅ Set' if bot_token and bot_token != 'YOUR_BOT_TOKEN' else '❌ Not set'}")
    print(f"   Chat IDs: {chat_ids}")
    print()
    
    if telegram_enabled and bot_token and bot_token != 'YOUR_BOT_TOKEN' and chat_ids:
        print("3️⃣  Sending Telegram notification...")
        try:
            checker.send_notification(stock_info)
            print("   ✅ Notification sent!")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    else:
        print("3️⃣  Skipping Telegram notification (not fully configured)")
        print("   💡 Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to enable")
    
    print()
    print("=" * 60)
    print("✅ Full flow test completed!")
    print("=" * 60)
    print()
    print("📊 Summary:")
    print(f"   ✅ API call: {'Success' if stock_info.get('method') == 'api' else 'Failed'}")
    print(f"   ✅ Stock detected: {stock_info.get('in_stock', False)}")
    print(f"   ✅ Available sizes: {len(stock_info.get('available_sizes', []))}")
    print(f"   ✅ Telegram: {'Ready' if telegram_enabled and bot_token and bot_token != 'YOUR_BOT_TOKEN' else 'Not configured'}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

