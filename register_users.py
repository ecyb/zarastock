#!/usr/bin/env python3
"""
Register all users from a Telegram channel/group
Adds them to chat_ids list for notifications
"""

import os
import json
import requests
from typing import List, Set

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')  # Channel/group ID to get users from
CONFIG_FILE = 'config.json'


def get_channel_members(channel_id: str) -> List[dict]:
    """Get all members from a Telegram channel/group."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return []
    
    # Note: Telegram Bot API doesn't allow getting channel members directly
    # You need to use getChatMembersCount or handle updates when users join
    # For groups, you can use getChatMembersCount
    # For channels, bots can't get member list unless they're admin
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMembersCount"
    params = {'chat_id': channel_id}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('ok'):
            count = data.get('result', 0)
            print(f"✅ Channel/Group has {count} members")
            print(f"⚠️  Note: Bot API cannot get member list directly")
            print(f"   You need to manually add chat_ids or use a bot that handles /start commands")
            return []
        else:
            print(f"❌ Error: {data.get('description', 'Unknown error')}")
            return []
    except Exception as e:
        print(f"❌ Error getting channel members: {e}")
        return []


def get_updates() -> List[dict]:
    """Get recent updates from Telegram (users who interacted with bot)."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return []
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {'timeout': 0}  # Get all pending updates
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('ok'):
            updates = data.get('result', [])
            users = []
            
            for update in updates:
                # Get user from message
                if 'message' in update:
                    user = update['message'].get('from')
                    if user:
                        users.append({
                            'id': str(user.get('id')),
                            'username': user.get('username', ''),
                            'first_name': user.get('first_name', ''),
                            'last_name': user.get('last_name', '')
                        })
                # Get user from callback query
                elif 'callback_query' in update:
                    user = update['callback_query'].get('from')
                    if user:
                        users.append({
                            'id': str(user.get('id')),
                            'username': user.get('username', ''),
                            'first_name': user.get('first_name', ''),
                            'last_name': user.get('last_name', '')
                        })
            
            # Remove duplicates
            seen = set()
            unique_users = []
            for user in users:
                if user['id'] not in seen:
                    seen.add(user['id'])
                    unique_users.append(user)
            
            return unique_users
        else:
            print(f"❌ Error: {data.get('description', 'Unknown error')}")
            return []
    except Exception as e:
        print(f"❌ Error getting updates: {e}")
        return []


def load_config() -> dict:
    """Load config.json."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    """Save config.json."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def register_users_from_updates():
    """Register all users who have interacted with the bot."""
    print("=" * 60)
    print("🔍 Registering users from Telegram bot updates...")
    print("=" * 60)
    print()
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set in environment")
        return
    
    # Get users from updates
    users = get_updates()
    
    if not users:
        print("⚠️  No users found in bot updates")
        print("   Users need to send /start or interact with the bot first")
        return
    
    print(f"📋 Found {len(users)} unique users:")
    for user in users:
        name = user.get('first_name', '') + (' ' + user.get('last_name', '') if user.get('last_name') else '')
        username = f"@{user.get('username')}" if user.get('username') else "no username"
        print(f"   - {name} ({username}) - ID: {user['id']}")
    
    print()
    
    # Load config
    config = load_config()
    if 'telegram' not in config:
        config['telegram'] = {}
    if 'chat_ids' not in config['telegram']:
        config['telegram']['chat_ids'] = []
    
    # Get existing chat IDs
    existing_ids = set(config['telegram']['chat_ids'])
    new_count = 0
    
    # Add new users
    for user in users:
        user_id = user['id']
        if user_id not in existing_ids:
            config['telegram']['chat_ids'].append(user_id)
            existing_ids.add(user_id)
            new_count += 1
            print(f"✅ Added user: {user['first_name']} (ID: {user_id})")
    
    if new_count == 0:
        print("ℹ️  No new users to add (all already registered)")
    else:
        # Save config
        save_config(config)
        print()
        print(f"✅ Registered {new_count} new user(s)")
        print(f"📊 Total registered users: {len(config['telegram']['chat_ids'])}")
    
    print()
    print("=" * 60)
    print("✅ Done!")
    print("=" * 60)


def register_from_channel():
    """Attempt to register users from a channel (limited by Telegram API)."""
    print("=" * 60)
    print("🔍 Attempting to get channel members...")
    print("=" * 60)
    print()
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set in environment")
        return
    
    if not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID not set in environment")
        print("   Set TELEGRAM_CHAT_ID to the channel/group ID")
        return
    
    # Get channel info
    get_channel_members(TELEGRAM_CHAT_ID)
    
    print()
    print("⚠️  Telegram Bot API limitations:")
    print("   - Bots cannot get member list from channels")
    print("   - Bots can only get member count (not individual IDs)")
    print("   - For groups, bot needs to be admin to get members")
    print()
    print("💡 Alternative: Use register_users_from_updates() to register")
    print("   users who interact with the bot via /start command")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--channel':
        register_from_channel()
    else:
        register_users_from_updates()

