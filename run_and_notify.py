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
    
    # Get products from config (load_config already handles ZARA_PRODUCTS env var)
    products = checker.config.get('products', [])
    if not products:
        print("❌ No products configured in config.json or ZARA_PRODUCTS env var")
        print("   Add products to config.json or set ZARA_PRODUCTS environment variable")
        print(f"   Current ZARA_PRODUCTS env: {os.getenv('ZARA_PRODUCTS', 'NOT SET')}")
        sys.exit(1)
    
    # load_config already handles ZARA_PRODUCTS and SKIP_NOSTOCK_NOTIFICATION from env vars
    zara_products_env = os.getenv('ZARA_PRODUCTS')
    skip_nostock_env = os.getenv('SKIP_NOSTOCK_NOTIFICATION')
    
    print("📋 Configuration:")
    if zara_products_env:
        print(f"   ✅ ZARA_PRODUCTS from env: {zara_products_env[:80]}..." if len(zara_products_env) > 80 else f"   ✅ ZARA_PRODUCTS from env: {zara_products_env}")
    else:
        print(f"   📄 Products from config.json: {len(products)} product(s)")
    
    if skip_nostock_env is not None:
        print(f"   ✅ SKIP_NOSTOCK_NOTIFICATION from env: {skip_nostock_env}")
    else:
        print(f"   📄 skip_nostock_notification from config.json: {checker.config.get('skip_nostock_notification', False)}")
    
    print(f"📦 Products to check: {len(products)}")
    for i, url in enumerate(products, 1):
        print(f"   {i}. {url}")
    print(f"⚙️  skip_nostock_notification: {checker.config.get('skip_nostock_notification', False)}")
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
    
    # Run once (cron job will call this script every 60 seconds)
    print("🔍 Running stock check...")
    print()
    
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
    
    print("=" * 60)
    print("✅ Done!")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

