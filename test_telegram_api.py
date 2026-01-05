#!/usr/bin/env python3
"""
Test Telegram notifications with API-based stock checking
"""

import os
import json
from dotenv import load_dotenv

# Load .env file (optional)
try:
    load_dotenv()
except:
    pass

# Mock stock info to test Telegram formatting
mock_stock_info_api = {
    'url': 'https://www.zara.com/itxrest/1/catalog/store/10706/product/id/483276547/availability',
    'name': 'Wool Double Breasted Coat',
    'price': '£199.00',
    'in_stock': True,
    'available_sizes': ['XS', 'S', 'M', 'L'],
    'timestamp': '2026-01-05T12:00:00',
    'method': 'api'
}

mock_stock_info_out = {
    'url': 'https://www.zara.com/itxrest/1/catalog/store/10706/product/id/483276547/availability',
    'name': 'Wool Double Breasted Coat',
    'price': '£199.00',
    'in_stock': False,
    'available_sizes': [],
    'timestamp': '2026-01-05T12:00:00',
    'method': 'api'
}

def test_telegram_message_formatting():
    """Test how Telegram messages are formatted."""
    print("=" * 60)
    print("🧪 Testing Telegram Message Formatting")
    print("=" * 60)
    print()
    
    try:
        from zara_stock_checker import ZaraStockChecker
        checker = ZaraStockChecker(verbose=True)
        
        # Check if Telegram is configured
        telegram_enabled = checker.config.get('telegram', {}).get('enabled', False)
        bot_token = checker.config.get('telegram', {}).get('bot_token', '')
        chat_ids = checker.config.get('telegram', {}).get('chat_ids', [])
        
        print("📱 Telegram Configuration:")
        print(f"   Enabled: {telegram_enabled}")
        print(f"   Bot Token: {'✅ Set' if bot_token and bot_token != 'YOUR_BOT_TOKEN' else '❌ Not set'}")
        print(f"   Chat IDs: {chat_ids if chat_ids else '❌ Not set'}")
        print()
        
        if not telegram_enabled or not bot_token or bot_token == 'YOUR_BOT_TOKEN':
            print("⚠️  Telegram not fully configured. Showing message preview only:")
            print()
            print("=" * 60)
            print("📨 IN STOCK MESSAGE PREVIEW:")
            print("=" * 60)
            
            # Simulate message creation
            is_in_stock = mock_stock_info_api.get('in_stock', False)
            product_name = mock_stock_info_api.get('name') or 'Zara Product'
            product_url = mock_stock_info_api.get('url', '')
            method = mock_stock_info_api.get('method', 'html')
            
            available_sizes = mock_stock_info_api.get('available_sizes', [])
            sizes_text = ', '.join(available_sizes) if available_sizes else 'Unknown'
            method_emoji = '🚀' if method == 'api' else '🌐'
            
            message = f"""✅ <b>Zara Item In Stock!</b> {method_emoji}

📦 <b>{product_name}</b>
💰 Price: {mock_stock_info_api.get('price', 'N/A')}
📏 Available Sizes: <b>{sizes_text}</b>

🔗 <a href="{product_url}">View Product</a>

⏰ Check it out now before it sells out!"""
            
            print(message)
            print()
            print("=" * 60)
            print("📨 OUT OF STOCK MESSAGE PREVIEW:")
            print("=" * 60)
            
            method_emoji = '🚀' if method == 'api' else '🌐'
            message = f"""❌ <b>Zara Item Out of Stock</b> {method_emoji}

📦 <b>{product_name}</b>
💰 Price: {mock_stock_info_api.get('price', 'N/A')}
📏 Status: <b>OUT OF STOCK</b>

🔗 <a href="{product_url}">View Product</a>

⏰ Will notify you when it's back in stock!"""
            
            print(message)
            print()
        else:
            print("✅ Telegram is configured! Testing with mock data...")
            print()
            
            # Test with in-stock item
            print("1️⃣  Testing IN STOCK notification...")
            try:
                checker.send_notification(mock_stock_info_api)
                print("   ✅ Notification sent!")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            print()
            
            # Test with out-of-stock item
            print("2️⃣  Testing OUT OF STOCK notification...")
            try:
                checker.send_notification(mock_stock_info_out)
                print("   ✅ Notification sent!")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
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
    import sys
    success = test_telegram_message_formatting()
    sys.exit(0 if success else 1)

