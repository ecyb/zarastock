import json
import os
import sys
from http.server import BaseHTTPRequestHandler
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


def load_config():
    """Load config.json."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_config(config):
    """Save config.json."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except (PermissionError, OSError) as e:
        print(f"⚠️  Cannot write to config.json (read-only filesystem?): {e}")
        print(f"   This is normal on Vercel. Users need to be registered manually via register_users.py")
        return False


def register_user(user_id: str, username: str = None, first_name: str = None):
    """Register a user by adding them to chat_ids in config.json."""
    config = load_config()
    
    if 'telegram' not in config:
        config['telegram'] = {}
    if 'chat_ids' not in config['telegram']:
        config['telegram']['chat_ids'] = []
    
    # Convert user_id to string for consistency
    user_id_str = str(user_id)
    
    # Check if user is already registered
    chat_ids = config['telegram']['chat_ids']
    if user_id_str in chat_ids:
        return False, "User already registered"
    
    # Add user to chat_ids
    chat_ids.append(user_id_str)
    
    # Try to save config
    saved = save_config(config)
    
    if not saved:
        # On read-only filesystem (e.g., Vercel), log the user info for manual registration
        user_info = {
            'id': user_id_str,
            'username': username,
            'first_name': first_name,
            'message': 'User pressed /start but config.json is read-only. Run register_users.py to add them.'
        }
        print(f"📝 User registration info (for manual registration): {json.dumps(user_info)}")
        return False, "Config file is read-only. Please run 'python3 register_users.py' to register users."
    
    return True, f"User {user_id_str} ({username or first_name or 'Unknown'}) registered successfully"


def send_telegram_message(chat_id: str, text: str):
    """Send a message via Telegram bot."""
    if not TELEGRAM_BOT_TOKEN:
        return None
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return None


def process_telegram_update(update: dict):
    """Process a Telegram bot update."""
    # Handle /start command
    if 'message' in update:
        message = update['message']
        text = message.get('text', '').strip()
        user = message.get('from')
        chat_id = str(message.get('chat', {}).get('id', ''))
        
        if not user:
            return
        
        user_id = str(user.get('id'))
        username = user.get('username')
        first_name = user.get('first_name', '')
        last_name = user.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip() or username or f"User {user_id}"
        
        if text == '/start':
            # Register the user
            registered, message_text = register_user(user_id, username, full_name)
            
            if registered:
                welcome_message = f"""✅ <b>Welcome!</b>

You've been registered for Zara stock notifications.

You'll receive notifications when the tracked items come back in stock.

To stop notifications, you can block the bot."""
            elif "already registered" in message_text.lower():
                welcome_message = f"""👋 <b>Welcome back!</b>

You're already registered for Zara stock notifications.

You'll continue to receive notifications when tracked items come back in stock."""
            else:
                # Config file is read-only (e.g., on Vercel)
                welcome_message = f"""👋 <b>Welcome!</b>

I received your /start command, but I cannot automatically register you because the configuration file is read-only.

Please contact the administrator to register you, or they can run:
<code>python3 register_users.py</code>

Your user ID: <code>{user_id}</code>
Your username: @{username or 'N/A'}"""
            
            send_telegram_message(chat_id, welcome_message)
            print(f"Processed /start from user {user_id} ({full_name}) - Registered: {registered}")
        
        elif text == '/status':
            # Check if user is registered
            config = load_config()
            chat_ids = config.get('telegram', {}).get('chat_ids', [])
            
            if user_id in chat_ids:
                status_message = f"""✅ <b>Status: Registered</b>

You're registered for Zara stock notifications.

Registered users: {len(chat_ids)}"""
            else:
                status_message = """❌ <b>Status: Not Registered</b>

You're not registered for notifications.

Send /start to register."""
            
            send_telegram_message(chat_id, status_message)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle POST requests from Telegram webhook."""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            # Parse JSON
            update = json.loads(body.decode('utf-8'))
            
            # Process the update
            process_telegram_update(update)
            
            # Send OK response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode())
        
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
        
        except Exception as e:
            print(f"Error processing webhook: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def do_GET(self):
        """Handle GET requests (for webhook verification)."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'service': 'telegram-webhook'}).encode())
    
    def log_message(self, format, *args):
        """Override to prevent default logging."""
        pass

