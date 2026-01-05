#!/usr/bin/env python3
"""
Zara Stock Checker
Monitors Zara product pages for stock availability and sends notifications.
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
        import re
        
        # Check if URL is already an API availability endpoint
        api_match = re.search(r'/store/(\d+)/product/id/(\d+)/availability', url)
        if api_match:
            store_id = int(api_match.group(1))
            product_id = int(api_match.group(2))
            return {'product_id': product_id, 'store_id': store_id}
        
        # Store ID mapping by country code
        store_map = {
            'uk': 10706,
            'gb': 10706,
            'us': 10701,
            'es': 10702,
            'fr': 10703,
            'it': 10704,
            'de': 10705,
            'nl': 10707,
            'be': 10708,
            'pt': 10709,
            'pl': 10710,
            'cz': 10711,
            'at': 10712,
            'ch': 10713,
            'ie': 10714,
            'dk': 10715,
            'se': 10716,
            'no': 10717,
            'fi': 10718,
        }
        
        # Extract country from URL
        country_match = re.search(r'/([a-z]{2})/en/', url)
        country = country_match.group(1) if country_match else 'uk'
        store_id = store_map.get(country, 10706)  # Default to UK
        
        # Known product ID mappings (for when page is blocked)
        # Format: product-page-slug -> product_id
        known_products = {
            'wool-double-breasted-coat-p08475319': 483276547,
            # Add more mappings as needed
        }
        
        # Reverse mapping: product_id -> product page URL
        # Format: product_id -> (country, slug)
        known_product_pages = {
            483276547: ('uk', 'wool-double-breasted-coat-p08475319'),
            # Add more mappings as needed
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
        
        # Fetch the page to get the actual product ID from JavaScript/JSON
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                html = response.text
                # Look for product ID in various places
                # Pattern 1: window.__PRELOADED_STATE__ or similar
                product_id_match = re.search(r'"productId"\s*:\s*"?(\d+)"?', html)
                if product_id_match:
                    product_id = int(product_id_match.group(1))
                    return {'product_id': product_id, 'store_id': store_id}
                
                # Pattern 2: In JSON-LD or structured data
                product_id_match = re.search(r'product[_-]?id["\']?\s*[:=]\s*["\']?(\d+)', html, re.I)
                if product_id_match:
                    product_id = int(product_id_match.group(1))
                    return {'product_id': product_id, 'store_id': store_id}
                
                # Pattern 3: In API calls in script tags (most reliable)
                api_match = re.search(r'/product/id/(\d+)', html)
                if api_match:
                    product_id = int(api_match.group(1))
                    return {'product_id': product_id, 'store_id': store_id}
                
                # Pattern 4: Look for availability API calls
                availability_match = re.search(r'/store/(\d+)/product/id/(\d+)/availability', html)
                if availability_match:
                    store_id = int(availability_match.group(1))
                    product_id = int(availability_match.group(2))
                    return {'product_id': product_id, 'store_id': store_id}
                
                # Pattern 5: Look in window.__PRELOADED_STATE__ or similar React state
                state_patterns = [
                    r'window\.__PRELOADED_STATE__\s*=\s*({.+?});',
                    r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                    r'"productId"\s*:\s*"?(\d+)"?',
                    r'"product_id"\s*:\s*"?(\d+)"?',
                ]
                
                for pattern in state_patterns:
                    matches = re.finditer(pattern, html, re.DOTALL)
                    for match in matches:
                        try:
                            if len(match.groups()) == 1 and match.group(1).isdigit():
                                # Direct product ID match
                                product_id = int(match.group(1))
                                return {'product_id': product_id, 'store_id': store_id}
                            elif len(match.groups()) == 1:
                                # JSON state - try to parse
                                state_str = match.group(1)
                                if state_str.startswith('{'):
                                    state_data = json.loads(state_str)
                                    # Try common paths
                                    product_id = (state_data.get('product', {}).get('id') or
                                                 state_data.get('productId') or
                                                 state_data.get('product_id'))
                                    if product_id:
                                        return {'product_id': int(product_id), 'store_id': store_id}
                        except:
                            continue
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Could not extract product ID from page: {e}")
                print(f"  💡 Tip: Use API URL directly: https://www.zara.com/itxrest/1/catalog/store/{store_id}/product/id/PRODUCT_ID/availability")
        
        # Last resort: if we have a product page URL pattern, suggest using API URL
        if '/uk/en/' in url and '-p' in url:
            if self.verbose:
                print(f"  ⚠️  Cannot extract product ID. Please use API URL directly in config.json")
                print(f"  💡 Example API URL format: https://www.zara.com/itxrest/1/catalog/store/10706/product/id/483276547/availability")
        
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
                    
                    for idx, item in enumerate(size_items):
                        # Try to find SKU ID in data attributes
                        sku_id = item.get('data-sku-id') or item.get('data-sku') or item.get('data-id')
                        if sku_id:
                            try:
                                sku_id = int(sku_id)
                            except:
                                continue
                        else:
                            # If no SKU ID in attributes, we'll need to match by order
                            # SKUs are ordered from smallest to largest
                            continue
                        
                        # Get size label
                        label = item.find('div', class_=re.compile(r'size-selector-sizes-size__label', re.I))
                        if label:
                            size_name = label.get_text(strip=True)
                            if size_name:
                                size_mapping[sku_id] = size_name
                    
                    if size_mapping:
                        return size_mapping
                    
                    # Fallback: Extract from JavaScript/JSON data
                    # Look for sizes array with SKU IDs
                    size_pattern = re.search(r'"sizes"\s*:\s*\[(.*?)\]', html, re.DOTALL)
                    if size_pattern:
                        sizes_json = '[' + size_pattern.group(1) + ']'
                        try:
                            sizes_data = json.loads(sizes_json)
                            size_mapping = {}
                            for size_item in sizes_data:
                                if isinstance(size_item, dict):
                                    sku_id = size_item.get('skuId') or size_item.get('sku') or size_item.get('id')
                                    size_name = size_item.get('name') or size_item.get('size') or size_item.get('label')
                                    if sku_id and size_name:
                                        try:
                                            size_mapping[int(sku_id)] = str(size_name)
                                        except:
                                            pass
                            if size_mapping:
                                return size_mapping
                        except:
                            pass
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Could not get size mapping: {e}")
        
        return None
    
    def _check_stock_via_api(self, url: str) -> Optional[Dict]:
        """Check stock using Zara's direct API endpoint (no browser needed)."""
        import re
        
        # Store original URL for product name fetching
        original_url = url
        product_page_url = None
        
        # Check if URL is already an API endpoint
        api_url = None
        if '/itxrest/' in url and '/availability' in url:
            api_url = url
            # Extract product_id and store_id from URL for later use
            match = re.search(r'/store/(\d+)/product/id/(\d+)/availability', url)
            if match:
                store_id = int(match.group(1))
                product_id = int(match.group(2))
                
                # Try to get product page URL from known mapping
                # Reverse mapping: product_id -> (country, slug)
                known_product_pages = {
                    483276547: ('uk', 'wool-double-breasted-coat-p08475319'),
                    # Add more mappings as needed
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
            product_page_url = url  # Save for later name fetching
            
            # Build API URL
            api_url = f"https://www.zara.com/itxrest/1/catalog/store/{store_id}/product/id/{product_id}/availability"
        
        print(f"  📡 Calling API: {api_url}")
        print(f"  📋 Request Headers:")
        api_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Referer': url,
            'Origin': 'https://www.zara.com',
        }
        for key, value in api_headers.items():
            print(f"     {key}: {value}")
        print()
        
        try:
            # Call the API
            response = self.session.get(api_url, headers=api_headers, timeout=10)
            
            print(f"  📥 Response Status: {response.status_code}")
            print(f"  📥 Response Headers:")
            for key, value in response.headers.items():
                if key.lower() in ['content-type', 'content-length', 'date']:
                    print(f"     {key}: {value}")
            print()
            
            if response.status_code != 200:
                print(f"  ❌ API returned status {response.status_code}")
                print(f"  📄 Response body: {response.text[:500]}")
                return None
            
            data = response.json()
            
            print(f"  ✅ Got API response:")
            print(f"  {json.dumps(data, indent=2)}")
            print()
            
            # Parse availability data
            skus_availability = data.get('skusAvailability', [])
            if not skus_availability:
                if self.verbose:
                    print("  ⚠️  No SKU availability data in response")
                return None
            
            print(f"  📊 Found {len(skus_availability)} SKUs in response")
            print(f"  📋 Raw SKU Availability:")
            for sku_info in skus_availability:
                sku_id = sku_info.get('sku')
                availability = sku_info.get('availability', 'unknown')
                print(f"     SKU {sku_id}: {availability}")
            print()
            
            # Log the exact SKU IDs for debugging
            sku_ids = [s.get('sku') for s in skus_availability]
            print(f"  🔍 SKU IDs received: {sku_ids}")
            print(f"  🔍 API URL called: {api_url}")
            print()
            
            # Get size mapping (SKU ID -> Size name)
            # First try to get from page, otherwise use generic size names based on order
            size_mapping = self._get_size_mapping_from_page(url)
            
            # If no mapping from page, create one based on order (SKUs are ordered XS to XL)
            if not size_mapping:
                # Sort SKUs by ID (smallest = XS, largest = XL)
                sorted_skus = sorted([s['sku'] for s in skus_availability])
                
                # Common size order for Zara
                size_names = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', '4', '6', '8', '10', '12', '14', '16', '18']
                
                # Create mapping: smallest SKU = first size, etc.
                size_mapping = {}
                for i, sku in enumerate(sorted_skus):
                    if i < len(size_names):
                        size_mapping[sku] = size_names[i]
                    else:
                        # For numeric sizes or beyond standard sizes
                        size_mapping[sku] = f"Size {i+1}"
                
                print(f"  📏 Created size mapping: {size_mapping}")
            
            # Parse available sizes with detailed output
            available_sizes = []
            in_stock = False
            
            print(f"  🔍 Checking availability for each size:")
            for sku_info in skus_availability:
                sku_id = sku_info.get('sku')
                availability = sku_info.get('availability', '').lower()
                
                # Map SKU to size name
                size_name = size_mapping.get(sku_id, f"SKU {sku_id}")
                
                # Check availability - explicitly check for out_of_stock
                # Only consider in_stock or low_on_stock as available
                is_available = False
                if availability == 'in_stock' or availability == 'low_on_stock':
                    is_available = True
                elif availability == 'out_of_stock':
                    is_available = False
                else:
                    # Unknown status - log it but don't consider available
                    if self.verbose:
                        print(f"     ⚠️  Unknown availability status: '{availability}' for SKU {sku_id}")
                    is_available = False
                
                status_emoji = "✅" if is_available else "❌"
                status_text = "IN STOCK" if is_available else "OUT OF STOCK"
                
                print(f"     {status_emoji} {size_name} (SKU {sku_id}): {status_text} (availability: '{availability}')")
                
                if is_available:
                    in_stock = True
                    available_sizes.append(size_name)
            
            # Check if we should only notify when ALL sizes are in stock
            notify_only_all_sizes = self.config.get('notify_only_all_sizes', False)
            min_sizes_in_stock = self.config.get('min_sizes_in_stock', 0)  # 0 = notify if any size is in stock
            
            # If notify_only_all_sizes is true, only mark as in_stock if ALL sizes are available
            if notify_only_all_sizes and len(available_sizes) < len(skus_availability):
                if self.verbose:
                    print(f"  ⚠️  notify_only_all_sizes=true: Only {len(available_sizes)}/{len(skus_availability)} sizes in stock, marking as OUT OF STOCK")
                in_stock = False
            # If min_sizes_in_stock is set, require at least that many sizes
            elif min_sizes_in_stock > 0 and len(available_sizes) < min_sizes_in_stock:
                if self.verbose:
                    print(f"  ⚠️  min_sizes_in_stock={min_sizes_in_stock}: Only {len(available_sizes)} sizes in stock, marking as OUT OF STOCK")
                in_stock = False
            
            print()
            print(f"  📈 Summary:")
            print(f"     Total SKUs: {len(skus_availability)}")
            print(f"     In Stock: {len(available_sizes)} ({', '.join(available_sizes) if available_sizes else 'None'})")
            print(f"     Out of Stock: {len(skus_availability) - len(available_sizes)}")
            print(f"     Overall Status: {'✅ IN STOCK' if in_stock else '❌ OUT OF STOCK'}")
            if notify_only_all_sizes:
                print(f"     ⚙️  notify_only_all_sizes: true (requires ALL sizes in stock)")
            elif min_sizes_in_stock > 0:
                print(f"     ⚙️  min_sizes_in_stock: {min_sizes_in_stock} (requires at least {min_sizes_in_stock} sizes)")
            print()
            
            # Get product name and price from the page (one-time fetch)
            # Use product_page_url if we have it (from product page), otherwise try original URL
            product_name = None
            product_price = None
            
            # Determine which URL to use for fetching product name
            page_url = product_page_url if product_page_url else (url if '/itxrest/' not in url else None)
            
            if page_url:
                try:
                    # Use a simple request without bot detection headers first
                    page_response = self.session.get(page_url, timeout=10)
                    if page_response.status_code == 200:
                        html = page_response.text
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Try JSON-LD first (most reliable)
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
                        
                        # Fallback: try to get from title tag
                        if not product_name:
                            title_tag = soup.find('title')
                            if title_tag:
                                title_text = title_tag.get_text(strip=True)
                                # Clean up title (remove " | ZARA" etc)
                                product_name = re.sub(r'\s*\|\s*ZARA.*$', '', title_text, flags=re.I).strip()
                        
                        # Fallback: try h1 tag
                        if not product_name:
                            h1_tag = soup.find('h1')
                            if h1_tag:
                                product_name = h1_tag.get_text(strip=True)
                except Exception as e:
                    if self.verbose:
                        print(f"  ⚠️  Could not fetch product name: {e}")
                    pass
            
            # Build result with all fields needed for notifications
            # Store original URL if it's a product page (for "View Product" link)
            # If we're using API URL, product_page_url should already be set from mapping above
            # If not set yet, try to construct it from known mapping
            if not product_page_url:
                if '/itxrest/' in url:
                    # Try to construct from known mapping
                    known_product_pages = {
                        483276547: ('uk', 'wool-double-breasted-coat-p08475319'),
                    }
                    if product_id in known_product_pages:
                        country, slug = known_product_pages[product_id]
                        product_page_url = f"https://www.zara.com/{country}/en/{slug}.html"
                        if self.verbose:
                            print(f"  ✅ Constructed product page URL: {product_page_url}")
                else:
                    # Original URL is a product page
                    product_page_url = url
            
            # Debug: Log the final in_stock value before building result
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
                'sizes': [{'size': s, 'available': True} for s in sorted(available_sizes)],  # For compatibility
                'product_page_url': product_page_url,  # Store product page URL for Telegram link
                'original_url': product_page_url  # Alias for compatibility
            }
            
            # Double-check the result
            if self.verbose:
                print(f"  ✅ Result built: in_stock={result.get('in_stock')}, available_sizes={result.get('available_sizes')}")
            
            # If we have API URL but no product name, try to get it from a product page
            # Extract product ID and try to find the product page
            if not product_name or product_name == 'Unknown Product':
                if '/itxrest/' in url:
                    # Try to find product page URL from API response or construct it
                    # We can't easily construct it without the display ID, but we can try
                    # to extract it from the API response if available
                    pass  # Will be handled by fallback HTML parsing if needed
            
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
        
        # Load from JSON file if it exists
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            # Return default config structure
            config = {
                "products": [],
                "telegram": {
                    "enabled": False,
                    "bot_token": "",
                    "chat_id": "",
                    "chat_ids": []
                },
                "check_interval": 300  # 5 minutes
            }
        
        # Override products from environment variable if set (for Railway/deployment)
        products_env = os.getenv('ZARA_PRODUCTS')
        if products_env:
            # Support comma-separated or newline-separated URLs
            products = [p.strip() for p in products_env.replace('\n', ',').split(',') if p.strip()]
            if products:
                config['products'] = products
        
        # Override with environment variables from .env file
        # Supports: api_key, TELEGRAM_BOT_TOKEN, TELEGRAM_API_KEY
        telegram_token = os.getenv('api_key') or os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_API_KEY')
        # Supports: chat_id, TELEGRAM_CHAT_ID
        telegram_chat_id = os.getenv('chat_id') or os.getenv('TELEGRAM_CHAT_ID')
        
        if telegram_token:
            if 'telegram' not in config:
                config['telegram'] = {}
            config['telegram']['bot_token'] = telegram_token
            # Auto-enable if both token and chat_id are found
            if telegram_token and telegram_chat_id:
                config['telegram']['enabled'] = True
        
        if telegram_chat_id:
            if 'telegram' not in config:
                config['telegram'] = {}
            config['telegram']['chat_id'] = telegram_chat_id
            # Also add to chat_ids list if not already there
            if 'chat_ids' not in config['telegram']:
                config['telegram']['chat_ids'] = []
            if telegram_chat_id not in config['telegram']['chat_ids']:
                config['telegram']['chat_ids'].append(telegram_chat_id)
        
        # Override skip_nostock_notification from environment variable if set
        skip_nostock_env = os.getenv('SKIP_NOSTOCK_NOTIFICATION')
        if skip_nostock_env is not None:
            # Support "true", "1", "yes" as true, anything else as false
            config['skip_nostock_notification'] = skip_nostock_env.lower() in ('true', '1', 'yes')
        
        return config
    
    def fetch_product_page(self, url: str) -> Optional[str]:
        """Fetch the HTML content of a Zara product page."""
        try:
            # Try with SSL verification first
            response = self.session.get(url, timeout=15, verify=True, allow_redirects=True)
            response.raise_for_status()
            html = response.text
            
            # Check if we got bot protection page
            if self._is_bot_protection_page(html):
                print("⚠️  Bot protection detected. The page may require browser automation.")
                print("   Consider using Selenium or wait a few seconds and try again.")
                return None
            
            return html
        except requests.exceptions.SSLError:
            # If SSL fails, try without verification (less secure but sometimes needed)
            try:
                print("⚠️  SSL verification failed, trying without verification...")
                response = self.session.get(url, timeout=15, verify=False, allow_redirects=True)
                response.raise_for_status()
                html = response.text
                
                if self._is_bot_protection_page(html):
                    print("⚠️  Bot protection detected. The page may require browser automation.")
                    return None
                
                return html
            except requests.RequestException as e:
                print(f"Error fetching {url}: {e}")
                return None
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def _is_bot_protection_page(self, html: str) -> bool:
        """Check if the HTML is a bot protection/interstitial page."""
        indicators = [
            'interstitial',
            'bm-verify',
            'akam-logo',
            'bot manager',
            'challenge',
            'verify you are human'
        ]
        html_lower = html.lower()
        return any(indicator in html_lower for indicator in indicators)
    
    def parse_stock_info(self, html: str, url: str) -> Dict:
        """Parse stock information from Zara product page HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        
        product_data = {}
        sizes = []
        json_ld_data = None  # Store JSON-LD data for later price extraction
        
        # Method 1: Look for JSON-LD structured data
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                json_ld_data = data  # Store for later use
                if isinstance(data, dict) and 'offers' in data:
                    product_data['name'] = data.get('name', 'Unknown Product')
                    price = data.get('offers', {}).get('price', '')
                    if price:
                        product_data['price'] = f"£{price}" if isinstance(price, (int, float)) else str(price)
            except:
                pass
        
        # Method 2: Look for window.__PRELOADED_STATE__ or similar React state
        scripts = soup.find_all('script')
        for script in scripts:
            if not script.string:
                continue
            
            script_text = script.string
            
            # Look for window.__PRELOADED_STATE__ or window.__INITIAL_STATE__
            state_patterns = [
                r'window\.__PRELOADED_STATE__\s*=\s*({.+?});',
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                r'__PRELOADED_STATE__\s*[:=]\s*({.+?})',
            ]
            
            for pattern in state_patterns:
                match = re.search(pattern, script_text, re.DOTALL)
                if match:
                    try:
                        state_data = json.loads(match.group(1))
                        # Navigate through the state to find product/size info
                        if isinstance(state_data, dict):
                            # Common paths in Zara's state
                            product_info = self._extract_from_state(state_data)
                            if product_info:
                                product_data.update(product_info)
                    except:
                        pass
            
            # Look for product data embedded in script tags
            if 'product' in script_text.lower() and ('size' in script_text.lower() or 'availability' in script_text.lower()):
                # Try to find JSON objects with size/availability info
                json_patterns = [
                    r'\{[^{}]*"sizes"[^{}]*\}',
                    r'\{[^{}]*"availability"[^{}]*\}',
                    r'\{[^{}]*"inStock"[^{}]*\}',
                ]
                
                for pattern in json_patterns:
                    matches = re.finditer(pattern, script_text, re.DOTALL)
                    for match in matches:
                        try:
                            data = json.loads(match.group())
                            if 'sizes' in data:
                                for size_info in data['sizes']:
                                    if isinstance(size_info, dict):
                                        if size_info.get('available', False) or size_info.get('inStock', False):
                                            sizes.append({
                                                'size': size_info.get('size', size_info.get('name', 'Unknown')),
                                                'available': True
                                            })
                        except:
                            pass
        
        # Method 3: Zara-specific size selector structure (popup/modal)
        # Look for the size selector: <div class="size-selector product-detail-size-selector-std__size-selector">
        # Note: This may be in a hidden modal/popup, but it's still in the HTML
        size_selector = soup.find('div', class_=re.compile(r'size-selector|product-detail-size-selector', re.I))
        if size_selector:
            if self.verbose:
                print("  Found Zara size selector container")
            
            # Look for the sizes list: <ul class="size-selector-sizes">
            sizes_list = size_selector.find('ul', class_=re.compile(r'size-selector-sizes', re.I))
            if sizes_list:
                if self.verbose:
                    print("  Found sizes list (ul.size-selector-sizes)")
                
                # Find all size items: <li class="size-selector-sizes__size size-selector-sizes-size size-selector-sizes-size--enabled">
                size_items = sizes_list.find_all('li', class_=re.compile(r'size-selector-sizes.*size', re.I))
                
                if self.verbose:
                    print(f"  Found {len(size_items)} size items in list")
                
                for item in size_items:
                    # Check if size is enabled (available)
                    # Available sizes have 'size-selector-sizes-size--enabled' class
                    classes = item.get('class', [])
                    class_str = ' '.join(classes) if classes else ''
                    is_enabled = 'size-selector-sizes-size--enabled' in class_str
                    
                    # Also check for data-qa-action="size-in-stock" on the button
                    button = item.find('button', attrs={'data-qa-action': 'size-in-stock'})
                    is_in_stock = button is not None
                    
                    # Check for "Few items left" or similar text in the item
                    item_text = item.get_text().lower()
                    has_few_items = 'few items' in item_text or 'few items left' in item_text
                    
                    # Check for disabled/unavailable indicators
                    is_disabled = 'disabled' in class_str or 'size-selector-sizes-size--disabled' in class_str
                    # Also check if item text contains "out of stock" or "unavailable"
                    is_unavailable_text = 'out of stock' in item_text or 'unavailable' in item_text or 'sold out' in item_text
                    
                    # Reduced verbose logging to avoid Railway rate limits
                    # Only log when actually finding a size
                    
                    # Consider available if: enabled OR in_stock OR has "few items" text, AND not disabled AND not unavailable
                    if (is_enabled or is_in_stock or has_few_items) and not is_disabled and not is_unavailable_text:
                        # Get the size label: <div class="size-selector-sizes-size__label">
                        label = item.find('div', class_=re.compile(r'size-selector-sizes-size__label', re.I))
                        if label:
                            size_text = label.get_text(strip=True)
                            if size_text and not any(s['size'] == size_text for s in sizes):
                                sizes.append({
                                    'size': size_text,
                                    'available': True
                                })
                                if self.verbose:
                                    print(f"    ✅ Found available size: {size_text} (enabled: {is_enabled}, in-stock: {is_in_stock})")
                        else:
                            # Fallback: get text from button or item itself
                            if button:
                                size_text = button.get_text(strip=True)
                            else:
                                size_text = item.get_text(strip=True)
                            
                            # Clean up the text (remove extra whitespace)
                            size_text = size_text.strip()
                            if size_text and len(size_text) < 10 and not any(s['size'] == size_text for s in sizes):
                                sizes.append({
                                    'size': size_text,
                                    'available': True
                                })
                                if self.verbose:
                                    print(f"    ✅ Found available size (fallback): {size_text}")
        
        # Also look for size selector anywhere in the page (in case it's not in the main container)
        if len(sizes) == 0:
            # Direct search for the sizes list
            sizes_list = soup.find('ul', class_=re.compile(r'size-selector-sizes', re.I))
            if sizes_list:
                if self.verbose:
                    print("  Found sizes list directly (not in container)")
                size_items = sizes_list.find_all('li', class_=re.compile(r'size-selector-sizes.*size', re.I))
                for item in size_items:
                    classes = item.get('class', [])
                    class_str = ' '.join(classes) if classes else ''
                    is_enabled = 'size-selector-sizes-size--enabled' in class_str
                    button = item.find('button', attrs={'data-qa-action': 'size-in-stock'})
                    is_in_stock = button is not None
                    
                    if (is_enabled or is_in_stock):
                        label = item.find('div', class_=re.compile(r'size-selector-sizes-size__label', re.I))
                        if label:
                            size_text = label.get_text(strip=True)
                            if size_text and not any(s['size'] == size_text for s in sizes):
                                sizes.append({'size': size_text, 'available': True})
                                if self.verbose:
                                    print(f"    ✅ Found available size (direct): {size_text}")
        
        # Method 3b: Look for other size selector patterns (fallback)
        if len(sizes) == 0:
            size_selectors = [
                {'class': re.compile(r'product-detail.*size', re.I)},
                {'class': re.compile(r'product.*size.*selector', re.I)},
                {'data-testid': re.compile(r'size', re.I)},
            ]
            
            for selector in size_selectors:
                size_container = soup.find(attrs=selector)
                if size_container:
                    if self.verbose:
                        print(f"  Found size container with selector: {selector}")
                    # Find all size buttons/items
                    size_items = size_container.find_all(['button', 'li', 'div', 'span', 'a', 'label'])
                    for item in size_items:
                        # Get size text
                        size_text = item.get_text(strip=True)
                        if not size_text or len(size_text) > 15:
                            continue
                        
                        # Check if it's a valid size - ONLY letter sizes to avoid matching prices/codes
                        # Exclude numbers and decimals (they're prices/product codes, not sizes)
                        size_pattern = r'^(XS|S|M|L|XL|XXL|XXXL)$'
                        if re.match(size_pattern, size_text, re.I):
                            # Check availability
                            classes = item.get('class', [])
                            class_str = ' '.join(classes).lower() if classes else ''
                            attrs_str = str(item.attrs).lower()
                            
                            is_disabled = (
                                item.get('disabled') is not None or
                                'disabled' in class_str or
                                'disabled' in attrs_str
                            )
                            
                            is_unavailable = (
                                'unavailable' in class_str or
                                'out-of-stock' in class_str or
                                'out' in class_str or
                                'sold-out' in class_str or
                                'not-available' in class_str or
                                'oos' in class_str
                            )
                            
                            # Check aria-label or title for availability hints
                            aria_label = item.get('aria-label', '').lower()
                            title = item.get('title', '').lower()
                            if 'out of stock' in aria_label or 'out of stock' in title:
                                is_unavailable = True
                            
                            # Reduce verbose logging to avoid Railway rate limits
                            # Only log if it's actually being added (not just checked)
                            
                            if not is_disabled and not is_unavailable:
                                # Avoid duplicates
                                if not any(s['size'] == size_text for s in sizes):
                                    sizes.append({
                                        'size': size_text,
                                        'available': True
                                    })
        
        # Method 3b: More aggressive search - look for any button/div with size-like text
        if len(sizes) == 0:
            if self.verbose:
                print("  No sizes found with selectors, trying aggressive search...")
            # Look for all buttons/clickable elements
            all_buttons = soup.find_all(['button', 'a', 'div'], 
                                      class_=re.compile(r'product|size|selector|option', re.I))
            for btn in all_buttons:
                text = btn.get_text(strip=True)
                # Only match letter sizes (XS, S, M, L, XL, XXL) - exclude numbers to avoid matching prices/codes
                if text and re.match(r'^(XS|S|M|L|XL|XXL|XXXL)$', text, re.I):
                    classes = btn.get('class', [])
                    class_str = ' '.join(classes).lower() if classes else ''
                    is_disabled = btn.get('disabled') is not None or 'disabled' in class_str
                    is_unavailable = 'unavailable' in class_str or 'out' in class_str or 'sold-out' in class_str
                    
                    if not is_disabled and not is_unavailable:
                        if not any(s['size'] == text for s in sizes):
                            sizes.append({'size': text, 'available': True})
                            if self.verbose:
                                print(f"    Found size via aggressive search: {text}")
        
        # Method 4: Look for data attributes
        size_buttons = soup.find_all(attrs={'data-size': True})
        for btn in size_buttons:
            size_name = btn.get('data-size', '').strip()
            if not size_name:
                continue
            
            classes = btn.get('class', [])
            class_str = ' '.join(classes).lower() if classes else ''
            
            is_disabled = btn.get('disabled') is not None or 'disabled' in class_str
            is_unavailable = 'unavailable' in class_str or 'out' in class_str or 'sold-out' in class_str
            
            if not is_disabled and not is_unavailable:
                if not any(s['size'] == size_name for s in sizes):
                    sizes.append({
                        'size': size_name,
                        'available': True
                    })
        
        # Get product name
        product_name = (
            soup.find('h1', class_=re.compile(r'product|title', re.I)) or
            soup.find('h1') or
            soup.find('title')
        )
        if product_name:
            product_data['name'] = product_name.get_text(strip=True)
        
        # Get price - Zara uses various price class names and structures
        price_selectors = [
            {'class': re.compile(r'product-detail-price', re.I)},
            {'class': re.compile(r'product.*price', re.I)},
            {'class': re.compile(r'price.*money', re.I)},
            {'class': re.compile(r'money.*price', re.I)},
            {'data-testid': re.compile(r'price', re.I)},
            {'itemprop': 'price'},
            {'class': re.compile(r'price', re.I)},
        ]
        
        for selector in price_selectors:
            price_elem = soup.find(attrs=selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Look for price patterns: £XX.XX, $XX.XX, €XX.XX, or just numbers with currency
                if price_text and (re.search(r'[£$€]\s*\d+', price_text) or re.search(r'\d+[.,]\d+', price_text)):
                    # Clean up price - Zara often shows "original price-discount%current price"
                    # Extract the last price (current price) or the most prominent one
                    # Look for patterns like "£69.50" or "69.50 GBP"
                    price_matches = re.findall(r'([£$€]?\s*\d+[.,]\d+)\s*(?:GBP|USD|EUR)?', price_text)
                    if price_matches:
                        # Take the last price (usually the current/discounted price)
                        current_price = price_matches[-1].strip()
                        # Add currency symbol if missing
                        if not re.match(r'^[£$€]', current_price):
                            # Try to detect currency from context
                            if 'GBP' in price_text or '£' in price_text:
                                current_price = '£' + current_price.replace('£', '')
                            elif 'USD' in price_text or '$' in price_text:
                                current_price = '$' + current_price.replace('$', '')
                            elif 'EUR' in price_text or '€' in price_text:
                                current_price = '€' + current_price.replace('€', '')
                            else:
                                current_price = '£' + current_price  # Default to GBP for UK site
                        product_data['price'] = current_price
                    else:
                        # Fallback: use the text as-is but clean it up
                        product_data['price'] = re.sub(r'\s+', ' ', price_text).strip()
                    if self.verbose:
                        print(f"  Found price: {product_data['price']}")
                    break
        
        # If still no price, try looking in meta tags or JSON-LD
        if not product_data.get('price') or product_data.get('price') == 'N/A':
            # Check meta tags
            price_meta = soup.find('meta', attrs={'property': 'product:price:amount'}) or \
                        soup.find('meta', attrs={'itemprop': 'price'})
            if price_meta:
                price_value = price_meta.get('content', '')
                price_currency = soup.find('meta', attrs={'property': 'product:price:currency'})
                currency = price_currency.get('content', '£') if price_currency else '£'
                if price_value:
                    product_data['price'] = f"{currency}{price_value}"
                    if self.verbose:
                        print(f"  Found price from meta: {product_data['price']}")
        
        # Try to find price in script tags (Zara often embeds prices in JSON)
        if not product_data.get('price') or product_data.get('price') == 'N/A':
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'price' in script.string.lower():
                    # Look for price patterns in script
                    price_match = re.search(r'["\']price["\']\s*:\s*["\']?([£$€]?\s*\d+[.,]?\d*)', script.string, re.I)
                    if price_match:
                        price_value = price_match.group(1)
                        if price_value:
                            product_data['price'] = price_value.strip()
                            if self.verbose:
                                print(f"  Found price from script: {product_data['price']}")
                            break
        
        # Check for "OUT OF STOCK" text in buttons (early detection for speed)
        out_of_stock_detected = False
        # Check for button with "OUT OF STOCK" text
        buttons = soup.find_all('button', class_=re.compile(r'product-detail', re.I))
        for btn in buttons:
            btn_text = btn.get_text(strip=True)
            if 'OUT OF STOCK' in btn_text.upper():
                out_of_stock_detected = True
                if self.verbose:
                    print("  ❌ Found 'OUT OF STOCK' button - item is completely out of stock")
                break
        
        # Check for "FEW ITEMS LEFT" or similar low stock indicators (means item IS in stock)
        few_items_left = False
        html_lower = html.lower()
        if 'few items left' in html_lower or 'few items' in html_lower:
            few_items_left = True
            if self.verbose:
                print("  ⚠️  Found 'FEW ITEMS LEFT' indicator - item is in stock but limited")
        
        # Also check for size availability indicators in the HTML
        # Look for sizes with "Few items left" text next to them
        if not few_items_left:
            # Check for text patterns that indicate stock
            stock_indicators = [
                r'few\s+items\s+left',
                r'only\s+\d+\s+left',
                r'low\s+stock',
                r'in\s+stock',
            ]
            for pattern in stock_indicators:
                if re.search(pattern, html_lower):
                    few_items_left = True
                    if self.verbose:
                        print(f"  ⚠️  Found stock indicator pattern: {pattern}")
                    break
        
        # Determine overall availability
        has_available_sizes = len(sizes) > 0
        
        # If explicitly marked as out of stock, override (item is completely out of stock)
        if out_of_stock_detected:
            has_available_sizes = False
            sizes = []  # Clear any sizes found (they shouldn't be there if out of stock)
        elif few_items_left and not has_available_sizes:
            # If we see "FEW ITEMS LEFT" but couldn't parse sizes, assume it's in stock
            # This handles cases where the HTML structure changed but stock indicator is visible
            has_available_sizes = True
            if self.verbose:
                print("  ✅ Item has 'FEW ITEMS LEFT' but sizes couldn't be parsed - marking as in stock")
        
        # If price is still N/A, try to extract from JSON-LD data we stored earlier
        final_price = product_data.get('price', 'N/A')
        if (final_price == 'N/A' or not final_price) and json_ld_data:
            try:
                # Try offers.price from JSON-LD
                price = json_ld_data.get('offers', {}).get('price', '')
                if price:
                    final_price = f"£{price}" if isinstance(price, (int, float)) else str(price)
            except:
                pass
        
        return {
            'url': url,
            'name': product_data.get('name', 'Unknown Product'),
            'price': final_price if final_price and final_price != 'N/A' else 'N/A',
            'sizes': sizes,
            'in_stock': has_available_sizes,
            'available_sizes': [s['size'] for s in sizes],
            'timestamp': datetime.now().isoformat()
        }
    
    def _extract_from_state(self, state: dict, depth: int = 0) -> Optional[Dict]:
        """Recursively extract product information from React state object."""
        if depth > 5:  # Prevent infinite recursion
            return None
        
        product_info = {}
        
        # Common keys that might contain product info
        for key in ['product', 'products', 'detail', 'details', 'item', 'items']:
            if key in state:
                value = state[key]
                if isinstance(value, dict):
                    # Check for name, price, sizes
                    if 'name' in value or 'title' in value:
                        product_info['name'] = value.get('name') or value.get('title')
                    if 'price' in value:
                        product_info['price'] = value.get('price')
                    if 'sizes' in value:
                        # Process sizes if present
                        pass
                    # Recurse deeper
                    deeper = self._extract_from_state(value, depth + 1)
                    if deeper:
                        product_info.update(deeper)
        
        return product_info if product_info else None
    
    def check_stock(self, url: str) -> Dict:
        """Check stock for a single product URL. Tries API first, falls back to HTML parsing."""
        print(f"Checking stock for: {url}")
        
        # Try API approach first (no browser needed, faster, no limits)
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
        
        html = self.fetch_product_page(url)
        
        if not html:
            return {
                'url': url,
                'error': 'Failed to fetch page - may be blocked by bot protection',
                'in_stock': False,
                'name': None,
                'price': None
            }
        
        stock_info = self.parse_stock_info(html, url)
        
        # If parsing returned null values, it likely failed
        if not stock_info.get('name') and len(html) > 0:
            # Check if we got a bot protection page
            if self._is_bot_protection_page(html):
                stock_info['error'] = 'Bot protection detected - page blocked'
            elif len(html) < 500:
                stock_info['error'] = 'Page content too short - may be blocked or incomplete'
            else:
                stock_info['error'] = 'Failed to parse product information from page'
        
        return stock_info
    
    def send_telegram_notification(self, product_info: Dict):
        """Send Telegram notification for product stock status using HTTP API to all registered users."""
        if not self.config.get('telegram', {}).get('enabled', False):
            return
        
        telegram_config = self.config['telegram']
        bot_token = telegram_config.get('bot_token', '')
        
        if not bot_token:
            print("⚠️  Telegram not configured properly (missing bot_token)")
            return
        
        # Skip if there's an error
        if 'error' in product_info:
            if self.verbose:
                print(f"⚠️  Skipping notification due to error: {product_info.get('error')}")
            return
        
        # Allow notifications even if name is missing (for API-based checks)
        # We'll use a generic name if needed
        product_name = product_info.get('name') or product_info.get('url', 'Unknown Product')
        
        # Get list of chat IDs to notify
        chat_ids = []
        
        # Add single chat_id if specified (backward compatibility)
        chat_id = telegram_config.get('chat_id', '')
        if chat_id:
            chat_ids.append(str(chat_id))
        
        # Add all chat_ids from list
        chat_ids_list = telegram_config.get('chat_ids', [])
        if chat_ids_list:
            chat_ids.extend([str(cid) for cid in chat_ids_list])
        
        # Remove duplicates
        chat_ids = list(set(chat_ids))
        
        if not chat_ids:
            print("⚠️  No chat IDs configured (add chat_id or chat_ids in config)")
            return
        
        try:
            is_in_stock = product_info.get('in_stock', False)
            product_name = product_info.get('name') or 'Zara Product'
            product_url = product_info.get('url', '')
            method = product_info.get('method', 'html')
            
            # Get available sizes - support both 'available_sizes' list and 'sizes' list format
            available_sizes = product_info.get('available_sizes', [])
            if not available_sizes and product_info.get('sizes'):
                # Extract from sizes list format
                available_sizes = [s.get('size', s) if isinstance(s, dict) else s 
                                 for s in product_info.get('sizes', []) 
                                 if isinstance(s, dict) and s.get('available', False) or not isinstance(s, dict)]
            
            # Get product page URL (prefer product page over API URL)
            view_url = product_url
            # If URL is an API endpoint, try to get product page URL from config or construct it
            if '/itxrest/' in product_url:
                # Try to get product page URL from the original request
                # Check if we have a product page URL stored
                original_url = product_info.get('original_url') or product_info.get('product_page_url')
                if original_url and '/itxrest/' not in original_url:
                    view_url = original_url
                else:
                    # Try to construct from product name or use a generic Zara URL
                    # For now, use the API URL but user should provide product page URL
                    pass
            
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
            
            # Send to all registered users
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
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            error_data = e.response.json()
                            print(f"   📄 Error response: {json.dumps(error_data, indent=6)}")
                        except:
                            print(f"   📄 Error response text: {e.response.text}")
            
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
    
    def monitor_products(self):
        """Continuously monitor all products in the config."""
        products = self.config.get('products', [])
        if not products:
            print("No products configured. Add URLs to config.json")
            return
        
        print(f"Monitoring {len(products)} product(s)...")
        print(f"Check interval: {self.config.get('check_interval', 300)} seconds\n")
        
        last_notified = {}  # Track last notification state per URL: {url: {'in_stock': bool, 'time': float}}
        
        while True:
            for product_url in products:
                try:
                    stock_info = self.check_stock(product_url)
                    
                    print(f"\n{'='*60}")
                    print(f"Product: {stock_info.get('name', 'Unknown')}")
                    print(f"URL: {stock_info['url']}")
                    print(f"In Stock: {'✅ YES' if stock_info.get('in_stock') else '❌ NO'}")
                    
                    if stock_info.get('available_sizes'):
                        print(f"Available Sizes: {', '.join(stock_info['available_sizes'])}")
                    
                    print(f"Timestamp: {stock_info.get('timestamp', 'N/A')}")
                    print(f"{'='*60}\n")
                    
                    # Send notification only when stock status CHANGES
                    url = stock_info['url']
                    current_in_stock = stock_info.get('in_stock', False)
                    last_state = last_notified.get(url, {})
                    last_in_stock = last_state.get('in_stock') if isinstance(last_state, dict) else None
                    last_notify_time = last_state.get('time', 0) if isinstance(last_state, dict) else (last_state if isinstance(last_state, (int, float)) else 0)
                    current_time = time.time()
                    
                    # Check if state changed (in-stock ↔ out-of-stock)
                    state_changed = (last_in_stock is None) or (last_in_stock != current_in_stock)
                    
                    # Also notify if it's been more than 24 hours (daily status update)
                    time_since_last = current_time - last_notify_time
                    should_notify_daily = time_since_last > 86400  # 24 hours
                    
                    if state_changed or should_notify_daily:
                        self.send_notification(stock_info)
                        last_notified[url] = {
                            'in_stock': current_in_stock,
                            'time': current_time
                        }
                    
                except Exception as e:
                    print(f"Error checking {product_url}: {e}")
                
                time.sleep(2)  # Small delay between products
            
            # Wait before next check cycle
            interval = self.config.get('check_interval', 300)
            print(f"\nWaiting {interval} seconds before next check...\n")
            time.sleep(interval)


def main():
    """Main entry point."""
    import sys
    
    # Check for verbose flag
    verbose = '-v' in sys.argv or '--verbose' in sys.argv
    if verbose:
        sys.argv = [arg for arg in sys.argv if arg not in ['-v', '--verbose']]
    
    checker = ZaraStockChecker(verbose=verbose)
    
    # If URL provided as command line argument, check it once
    if len(sys.argv) > 1:
        url = sys.argv[1]
        stock_info = checker.check_stock(url)
        
        print("\n" + "="*60)
        print("STOCK CHECK RESULT")
        print("="*60)
        print(json.dumps(stock_info, indent=2))
        print("="*60)
        
        # Save HTML for debugging
        html = checker.fetch_product_page(url)
        if html:
            with open('last_check.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("\nHTML saved to 'last_check.html' for debugging")
    else:
        # Run continuous monitoring
        checker.monitor_products()


if __name__ == "__main__":
    main()

