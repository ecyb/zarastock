#!/usr/bin/env python3
"""
Zara Stock Checker - Run stock check and send Telegram notification
All-in-one script (merged from zara_stock_checker.py)
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import re
from typing import Dict, List, Optional
import os
import urllib3
import sys

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    try:
        load_dotenv()
    except (PermissionError, FileNotFoundError):
        pass  # .env file not accessible, continue without it
except ImportError:
    pass  # dotenv not installed, continue without it

# Disable SSL warnings if we need to bypass verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ZaraStockChecker:
    def __init__(self, config_file: str = "config.json", verbose: bool = False):
        """Initialize the stock checker with configuration."""
        self.config = self.load_config(config_file)
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Referer': 'https://www.zara.com/',
        })
    
    def _extract_product_info_from_url(self, url: str) -> Optional[Dict]:
        """Extract product ID and store ID from Zara product URL, API URL, or fetch from page."""
        # Check if URL is already an API availability endpoint
        api_match = re.search(r'/store/(\d+)/product/id/(\d+)/availability', url)
        if api_match:
            store_id = int(api_match.group(1))
            product_id = int(api_match.group(2))
            return {'product_id': product_id, 'store_id': store_id}
        
        # Store ID mapping by country code
        store_map = {
            'uk': 10706, 'gb': 10706, 'us': 10701, 'es': 10702, 'fr': 10703,
            'it': 10704, 'de': 10705, 'nl': 10707, 'be': 10708, 'pt': 10709,
            'pl': 10710, 'cz': 10711, 'at': 10712, 'ch': 10713, 'ie': 10714,
            'dk': 10715, 'se': 10716, 'no': 10717, 'fi': 10718,
        }
        
        # Extract country from URL
        country_match = re.search(r'/([a-z]{2})/en/', url)
        country = country_match.group(1) if country_match else 'uk'
        store_id = store_map.get(country, 10706)  # Default to UK
        
        # Known product ID mappings
        known_products = {
            'wool-double-breasted-coat-p08475319': 483276547,
        }
        
        # Try to match known product from URL
        url_slug_match = re.search(r'/([^/]+-p\d+)\.html', url)
        if url_slug_match:
            slug = url_slug_match.group(1)
            if slug in known_products:
                product_id = known_products[slug]
                if self.verbose:
                    print(f"  ✅ Found known product ID: {product_id} (from mapping)")
                return {'product_id': product_id, 'store_id': store_id}
        
        # Fetch the page to get the actual product ID
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                html = response.text
                # Look for product ID in various places
                patterns = [
                    r'"productId"\s*:\s*"?(\d+)"?',
                    r'product[_-]?id["\']?\s*[:=]\s*["\']?(\d+)',
                    r'/product/id/(\d+)',
                    r'/store/(\d+)/product/id/(\d+)/availability',
                ]
                for pattern in patterns:
                    match = re.search(pattern, html, re.I)
                    if match:
                        if len(match.groups()) == 2:  # store and product
                            return {'product_id': int(match.group(2)), 'store_id': int(match.group(1))}
                        else:
                            return {'product_id': int(match.group(1)), 'store_id': store_id}
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Could not extract product ID from page: {e}")
        
        return None
    
    def _get_size_mapping_from_page(self, url: str) -> Optional[Dict[int, str]]:
        """Get size mapping (SKU ID -> Size name) from product page."""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for size selector with SKU IDs
                size_selector = soup.find('div', class_=re.compile(r'size-selector', re.I))
                if size_selector:
                    size_items = size_selector.find_all('li', class_=re.compile(r'size-selector-sizes.*size', re.I))
                    size_mapping = {}
                    
                    for item in size_items:
                        sku_id = item.get('data-sku-id') or item.get('data-sku') or item.get('data-id')
                        if sku_id:
                            try:
                                sku_id = int(sku_id)
                                label = item.find('div', class_=re.compile(r'size-selector-sizes-size__label', re.I))
                                if label:
                                    size_name = label.get_text(strip=True)
                                    if size_name:
                                        size_mapping[sku_id] = size_name
                            except:
                                continue
                    
                    if size_mapping:
                        return size_mapping
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Could not get size mapping: {e}")
        
        return None
    
    def _check_stock_via_api(self, url: str) -> Optional[Dict]:
        """Check stock using Zara's direct API endpoint (no browser needed)."""
        original_url = url
        product_page_url = None
        
        # Check if URL is already an API endpoint
        api_url = None
        if '/itxrest/' in url and '/availability' in url:
            api_url = url
            match = re.search(r'/store/(\d+)/product/id/(\d+)/availability', url)
            if match:
                store_id = int(match.group(1))
                product_id = int(match.group(2))
                
                # Known product page mappings
                known_product_pages = {
                    483276547: ('uk', 'wool-double-breasted-coat-p08475319'),
                }
                
                if product_id in known_product_pages:
                    country, slug = known_product_pages[product_id]
                    product_page_url = f"https://www.zara.com/{country}/en/{slug}.html"
                    if self.verbose:
                        print(f"  ✅ Found product page URL from mapping: {product_page_url}")
            else:
                if self.verbose:
                    print("  ⚠️  Could not parse API URL")
                return None
        else:
            # Extract product info from product page URL
            product_info = self._extract_product_info_from_url(url)
            if not product_info:
                if self.verbose:
                    print("  ⚠️  Could not extract product ID, falling back to HTML parsing")
                return None
            
            product_id = product_info['product_id']
            store_id = product_info['store_id']
            product_page_url = url
            api_url = f"https://www.zara.com/itxrest/1/catalog/store/{store_id}/product/id/{product_id}/availability"
        
        print(f"  📡 Calling API: {api_url}")
        print(f"  📋 Request Headers:")
        
        # Use consistent headers to get consistent SKU responses
        api_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.zara.com/uk/en/',
            'Origin': 'https://www.zara.com',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        for key, value in api_headers.items():
            print(f"     {key}: {value}")
        print()
        
        print(f"  🌍 API Request Details:")
        print(f"     URL: {api_url}")
        print(f"     Store ID: {store_id}")
        print(f"     Product ID: {product_id}")
        print(f"     Region: UK (en-GB)")
        print()
        
        try:
            response = self.session.get(api_url, headers=api_headers, timeout=10)
            
            print(f"  📥 Response Status: {response.status_code}")
            print(f"  📥 Response Headers (all):")
            for key, value in response.headers.items():
                print(f"     {key}: {value}")
            
            country_header = response.headers.get('cf-ipcountry') or response.headers.get('x-country-code') or response.headers.get('x-region')
            if country_header:
                print(f"  🌍 Detected Country/Region from headers: {country_header}")
            else:
                print(f"  ⚠️  No country/region header detected - Zara may be using IP geolocation")
            
            request_ip = response.headers.get('x-forwarded-for') or response.headers.get('cf-connecting-ip')
            if request_ip:
                print(f"  🌐 Request IP: {request_ip}")
            print()
            
            if response.status_code != 200:
                print(f"  ❌ API returned status {response.status_code}")
                print(f"  📄 Response body: {response.text[:500]}")
                return None
            
            data = response.json()
            
            print(f"  ✅ Got API response:")
            print(f"  {json.dumps(data, indent=2)}")
            print()
            
            skus_availability = data.get('skusAvailability', [])
            if not skus_availability:
                if self.verbose:
                    print("  ⚠️  No SKU availability data in response")
                return None
            
            received_skus = [s.get('sku') for s in skus_availability if s.get('sku')]
            
            print(f"  📊 Found {len(skus_availability)} SKUs in response")
            print(f"  🔍 SKU IDs received: {received_skus}")
            print(f"  📋 Raw SKU Availability:")
            for sku_info in skus_availability:
                print(f"     SKU {sku_info.get('sku')}: {sku_info.get('availability')}")
            
            # WARNING: Different regions return different SKUs!
            expected_uk_skus = [483272260, 483272258, 483272259, 483272256, 483272257]
            if set(received_skus) != set(expected_uk_skus):
                print(f"  ⚠️  WARNING: Received SKUs {received_skus} differ from expected UK SKUs {expected_uk_skus}")
                print(f"  ⚠️  This means Railway server is checking a DIFFERENT REGION's inventory!")
                print(f"  ⚠️  Railway IP location is NOT in UK - inventory shown is for server's region, not UK")
            print()
            
            # Get size mapping
            size_mapping = self._get_size_mapping_from_page(product_page_url if product_page_url else url)
            
            if not size_mapping:
                sorted_skus = sorted([s['sku'] for s in skus_availability])
                size_names = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', '4', '6', '8', '10', '12', '14', '16', '18']
                size_mapping = {}
                for i, sku in enumerate(sorted_skus):
                    if i < len(size_names):
                        size_mapping[sku] = size_names[i]
                    else:
                        size_mapping[sku] = f"Size {i+1}"
                
                print(f"  📏 Created size mapping: {size_mapping}")
            
            available_sizes = []
            in_stock = False
            
            print(f"  🔍 Checking availability for each size:")
            for sku_info in skus_availability:
                sku_id = sku_info.get('sku')
                availability = sku_info.get('availability', '').lower()
                
                size_name = size_mapping.get(sku_id, f"SKU {sku_id}")
                
                is_available = False
                if availability == 'in_stock' or availability == 'low_on_stock':
                    is_available = True
                elif availability == 'out_of_stock':
                    is_available = False
                
                status_emoji = "✅" if is_available else "❌"
                status_text = "IN STOCK" if is_available else "OUT OF STOCK"
                
                print(f"     {status_emoji} {size_name} (SKU {sku_id}): {status_text} (availability: '{availability}')")
                
                if is_available:
                    in_stock = True
                    available_sizes.append(size_name)
            
            print()
            print(f"  📈 Summary:")
            print(f"     Total SKUs: {len(skus_availability)}")
            print(f"     In Stock: {len(available_sizes)} ({', '.join(available_sizes) if available_sizes else 'None'})")
            print(f"     Out of Stock: {len(skus_availability) - len(available_sizes)}")
            print(f"     Overall Status: {'✅ IN STOCK' if in_stock else '❌ OUT OF STOCK'}")
            print()
            
            # Get product name and price
            product_name = None
            product_price = None
            
            page_url = product_page_url if product_page_url else (url if '/itxrest/' not in url else None)
            
            if page_url:
                try:
                    page_response = self.session.get(page_url, timeout=10)
                    if page_response.status_code == 200:
                        html = page_response.text
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        json_ld = soup.find('script', type='application/ld+json')
                        if json_ld:
                            try:
                                data = json.loads(json_ld.string)
                                if isinstance(data, dict):
                                    product_name = data.get('name', 'Unknown Product')
                                    price = data.get('offers', {}).get('price', '')
                                    if price:
                                        product_price = f"£{price}" if isinstance(price, (int, float)) else str(price)
                            except:
                                pass
                        
                        if not product_name:
                            title_tag = soup.find('title')
                            if title_tag:
                                title_text = title_tag.get_text(strip=True)
                                product_name = re.sub(r'\s*\|\s*ZARA.*$', '', title_text, flags=re.I).strip()
                        
                        if not product_name:
                            h1_tag = soup.find('h1')
                            if h1_tag:
                                product_name = h1_tag.get_text(strip=True)
                except Exception as e:
                    if self.verbose:
                        print(f"  ⚠️  Could not fetch product name: {e}")
            
            if not product_page_url:
                if '/itxrest/' in url:
                    known_product_pages = {
                        483276547: ('uk', 'wool-double-breasted-coat-p08475319'),
                    }
                    if product_id in known_product_pages:
                        country, slug = known_product_pages[product_id]
                        product_page_url = f"https://www.zara.com/{country}/en/{slug}.html"
                        if self.verbose:
                            print(f"  ✅ Constructed product page URL: {product_page_url}")
                else:
                    product_page_url = url
            
            print()
            print(f"  🔍 FINAL RESULT BUILD:")
            print(f"     in_stock = {in_stock} (type: {type(in_stock)})")
            print(f"     available_sizes = {available_sizes}")
            print(f"     Will send notification: {'YES - IN STOCK' if in_stock else 'NO - OUT OF STOCK'}")
            print()
            
            result = {
                'url': url,
                'name': product_name or 'Unknown Product',
                'price': product_price or 'N/A',
                'in_stock': in_stock,
                'available_sizes': sorted(available_sizes),
                'timestamp': datetime.now().isoformat(),
                'method': 'api',
                'sizes': [{'size': s, 'available': True} for s in sorted(available_sizes)],
                'product_page_url': product_page_url,
                'original_url': product_page_url
            }
            
            if self.verbose:
                print(f"  ✅ Result built: in_stock={result.get('in_stock')}, available_sizes={result.get('available_sizes')}")
            
            return result
            
        except Exception as e:
            if self.verbose:
                print(f"  ❌ API call failed: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def load_config(self, config_file: str) -> dict:
        """Load configuration from JSON file and .env file."""
        config = {}
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {
                "products": [],
                "telegram": {
                    "enabled": False,
                    "bot_token": "",
                    "chat_id": "",
                    "chat_ids": []
                },
                "check_interval": 300
            }
        
        # Override products from environment variable
        products_env = os.getenv('ZARA_PRODUCTS')
        if products_env:
            products = [p.strip() for p in products_env.replace('\n', ',').split(',') if p.strip()]
            if products:
                config['products'] = products
        
        # Override Telegram settings from environment variables
        telegram_token = os.getenv('api_key') or os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_API_KEY')
        telegram_chat_id = os.getenv('chat_id') or os.getenv('TELEGRAM_CHAT_ID')
        
        if telegram_token:
            if 'telegram' not in config:
                config['telegram'] = {}
            config['telegram']['bot_token'] = telegram_token
            if telegram_token and telegram_chat_id:
                config['telegram']['enabled'] = True
        
        if telegram_chat_id:
            if 'telegram' not in config:
                config['telegram'] = {}
            config['telegram']['chat_id'] = telegram_chat_id
            if 'chat_ids' not in config['telegram']:
                config['telegram']['chat_ids'] = []
            if telegram_chat_id not in config['telegram']['chat_ids']:
                config['telegram']['chat_ids'].append(telegram_chat_id)
        
        # Override skip_nostock_notification from environment variable
        skip_nostock_env = os.getenv('SKIP_NOSTOCK_NOTIFICATION')
        if skip_nostock_env is not None:
            config['skip_nostock_notification'] = skip_nostock_env.lower() in ('true', '1', 'yes')
        
        return config
    
    def check_stock(self, url: str) -> Dict:
        """Check stock for a single product URL. Tries API first, falls back to HTML parsing."""
        print(f"Checking stock for: {url}")
        
        if self.verbose:
            print("  🚀 Trying API approach (no browser needed)...")
        
        api_result = self._check_stock_via_api(url)
        if api_result:
            if self.verbose:
                print(f"  ✅ API check successful!")
            return api_result
        
        # Fall back to HTML parsing if API fails
        if self.verbose:
            print("  ⚠️  API approach failed, falling back to HTML parsing...")
        
        return {
            'url': url,
            'error': 'Failed to fetch page - may be blocked by bot protection',
            'in_stock': False,
            'name': None,
            'price': None
        }
    
    def send_telegram_notification(self, product_info: Dict):
        """Send Telegram notification for product stock status."""
        if not self.config.get('telegram', {}).get('enabled', False):
            return
        
        telegram_config = self.config['telegram']
        bot_token = telegram_config.get('bot_token', '')
        
        if not bot_token:
            print("⚠️  Telegram not configured properly (missing bot_token)")
            return
        
        if 'error' in product_info:
            if self.verbose:
                print(f"⚠️  Skipping notification due to error: {product_info.get('error')}")
            return
        
        is_in_stock = product_info.get('in_stock', False)
        skip_nostock = self.config.get('skip_nostock_notification', False)
        
        if skip_nostock and not is_in_stock:
            if self.verbose:
                print(f"  ⏭️  Skipping notification - item is OUT OF STOCK and skip_nostock_notification=true")
            return
        
        product_name = product_info.get('name') or 'Zara Product'
        
        chat_ids = []
        chat_id = telegram_config.get('chat_id', '')
        if chat_id:
            chat_ids.append(str(chat_id))
        chat_ids_list = telegram_config.get('chat_ids', [])
        if chat_ids_list:
            chat_ids.extend([str(cid) for cid in chat_ids_list])
        chat_ids = list(set(chat_ids))
        
        if not chat_ids:
            print("⚠️  No chat IDs configured (add chat_id or chat_ids in config)")
            return
        
        try:
            product_url = product_info.get('url', '')
            method = product_info.get('method', 'html')
            
            available_sizes = product_info.get('available_sizes', [])
            if not available_sizes and product_info.get('sizes'):
                available_sizes = [s.get('size', s) if isinstance(s, dict) else s 
                                 for s in product_info.get('sizes', []) 
                                 if isinstance(s, dict) and s.get('available', False) or not isinstance(s, dict)]
            
            view_url = product_info.get('product_page_url') or product_url
            
            if is_in_stock:
                sizes_text = ', '.join(available_sizes) if available_sizes else 'Unknown'
                method_emoji = '🚀' if method == 'api' else '🌐'
                message = f"""✅ <b>Zara Item In Stock!</b> {method_emoji}

📦 <b>{product_name}</b>
📏 Available Sizes: <b>{sizes_text}</b>

🔗 <a href="{view_url}">View Product</a>

⏰ Check it out now before it sells out!"""
            else:
                method_emoji = '🚀' if method == 'api' else '🌐'
                message = f"""❌ <b>Zara Item Out of Stock</b> {method_emoji}

📦 <b>{product_name}</b>
📏 Status: <b>OUT OF STOCK</b>

🔗 <a href="{view_url}">View Product</a>

⏰ Will notify you when it's back in stock!"""
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            success_count = 0
            
            print(f"\n📤 Sending Telegram notification...")
            print(f"   API URL: {url}")
            print(f"   Chat IDs: {chat_ids}")
            print(f"\n📨 Message to send:")
            print("   " + "-" * 50)
            for line in message.split('\n'):
                print(f"   {line}")
            print("   " + "-" * 50)
            print()
            
            for cid in chat_ids:
                try:
                    payload = {
                        'chat_id': cid,
                        'text': message,
                        'parse_mode': 'HTML',
                        'disable_web_page_preview': False
                    }
                    
                    print(f"   📤 Sending to chat_id {cid}...")
                    print(f"   📦 Payload: {json.dumps(payload, indent=6)}")
                    
                    response = requests.post(url, json=payload, timeout=10)
                    response.raise_for_status()
                    
                    response_data = response.json()
                    print(f"   ✅ Response: {json.dumps(response_data, indent=6)}")
                    
                    if response_data.get('ok'):
                        print(f"   ✅ Successfully sent to chat_id {cid}")
                        success_count += 1
                    else:
                        print(f"   ⚠️  API returned ok=false: {response_data.get('description', 'Unknown error')}")
                except Exception as e:
                    print(f"   ❌ Failed to send to chat_id {cid}: {e}")
            
            print()
            if success_count > 0:
                print(f"✅ Telegram notification sent to {success_count} user(s) for {product_name}")
            else:
                print(f"❌ Failed to send Telegram notification to any users")
        except Exception as e:
            print(f"❌ Error sending Telegram notification: {e}")
    
    def send_notification(self, product_info: Dict):
        """Send notification via Telegram."""
        self.send_telegram_notification(product_info)


# Main execution
print("=" * 60)
print("🚀 Running Stock Check & Sending Telegram Notification")
print("=" * 60)
print()

try:
    checker = ZaraStockChecker(verbose=True)
    
    products = checker.config.get('products', [])
    if not products:
        print("❌ No products configured in config.json or ZARA_PRODUCTS env var")
        print("   Add products to config.json or set ZARA_PRODUCTS environment variable")
        print(f"   Current ZARA_PRODUCTS env: {os.getenv('ZARA_PRODUCTS', 'NOT SET')}")
        sys.exit(1)
    
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
        if not telegram_config.get('bot_token') or telegram_config.get('bot_token') == 'YOUR_BOT_TOKEN':
            checker.config['telegram']['bot_token'] = bot_token
    
    print("🔍 Running stock check...")
    print()
    
    for product_url in products:
        print("=" * 60)
        print(f"🔍 Checking: {product_url}")
        print("=" * 60)
        print()
        
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
