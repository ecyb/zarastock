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

print("=" * 60)
print("🚀 Running Stock Check & Sending Telegram Notification")
print("=" * 60)
print()

try:
    from zara_stock_checker import ZaraStockChecker
    import time
    
    checker = ZaraStockChecker(verbose=True)
    
    # Get products from config (same as app.py)
    products = checker.config.get('products', [])
    if not products:
        print("❌ No products configured in config.json or ZARA_PRODUCTS env var")
        print("   Add products to config.json or set ZARA_PRODUCTS environment variable")
        sys.exit(1)
    
    # Get check interval from config (default: 60 seconds)
    check_interval = checker.config.get('check_interval', 60)
    print(f"⏰ Check interval: {check_interval} seconds")
    print(f"📦 Products to check: {len(products)}")
    for i, url in enumerate(products, 1):
        print(f"   {i}. {url}")
    print()
    
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
    
    # Run in a loop (like a scheduled task)
    print("🔄 Starting continuous stock checking loop...")
    print("   Press CTRL+C to stop")
    print()
    
    while True:
        try:
            for product_url in products:
                print("=" * 60)
                print(f"🔍 Checking: {product_url}")
                print("=" * 60)
                print()
                
                # Check stock
                stock_info = checker.check_stock(product_url)
                
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
                
                # Send notification (send_notification handles skip_nostock_notification logic)
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
            
            # Wait before next check
            print(f"⏳ Waiting {check_interval} seconds until next check...")
            print()
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            print("\n\n🛑 Stopped by user")
            break
        except Exception as e:
            print(f"❌ Error in check loop: {e}")
            import traceback
            traceback.print_exc()
            print(f"⏳ Waiting {check_interval} seconds before retry...")
            time.sleep(check_interval)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

