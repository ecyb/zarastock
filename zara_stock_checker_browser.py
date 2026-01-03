#!/usr/bin/env python3
"""
Zara Stock Checker using undetected-chromedriver (best for bypassing bot protection)
Requires: pip install undetected-chromedriver
"""

try:
    import ssl
    # Fix SSL certificate issues on macOS
    ssl._create_default_https_context = ssl._create_unverified_context
    import undetected_chromedriver as uc
    UC_AVAILABLE = True
except ImportError:
    UC_AVAILABLE = False
    print("⚠️  undetected-chromedriver not installed. Install with: pip install undetected-chromedriver")

from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
from typing import Dict, Optional
import sys
import os

# Import the parsing logic from the main checker
from zara_stock_checker import ZaraStockChecker


class ZaraStockCheckerBrowser(ZaraStockChecker):
    """Zara stock checker using undetected-chromedriver to bypass bot protection."""
    
    def __init__(self, config_file: str = "config.json", verbose: bool = False, headless: bool = True):
        """Initialize with undetected Chrome webdriver."""
        if not UC_AVAILABLE:
            raise ImportError("undetected-chromedriver is required. Install with: pip install undetected-chromedriver")
        
        super().__init__(config_file, verbose)
        self.headless = headless
        self.driver = None
        self._setup_driver()
    
    def _setup_driver(self):
        """Setup undetected Chrome WebDriver (local) or regular Selenium (Docker)."""
        try:
            import os
            is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
            
            # In Docker, use regular Selenium (more stable, headless anyway)
            if is_docker:
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from selenium.webdriver.chrome.options import Options
                
                chrome_options = Options()
                chrome_options.add_argument('--headless=new')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                
                # Find Chromium binary
                chrome_binaries = [
                    '/usr/bin/chromium',
                    '/usr/bin/chromium-browser',
                    '/usr/bin/google-chrome-stable',
                    '/usr/bin/google-chrome'
                ]
                
                chrome_bin = None
                for bin_path in chrome_binaries:
                    if os.path.exists(bin_path):
                        chrome_bin = bin_path
                        chrome_options.binary_location = bin_path
                        if self.verbose:
                            print(f"  Using browser: {bin_path}")
                        break
                
                # Find ChromeDriver
                import shutil
                chromedriver_path = shutil.which('chromedriver') or '/usr/bin/chromedriver'
                
                if os.path.exists(chromedriver_path):
                    service = Service(chromedriver_path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    # Let Selenium auto-detect
                    self.driver = webdriver.Chrome(options=chrome_options)
                
                print("✅ Browser driver initialized (Selenium in Docker)")
            else:
                # Local: use undetected-chromedriver (better bot protection bypass)
                options = uc.ChromeOptions()
                if self.headless:
                    options.add_argument('--headless=new')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--disable-features=IsolateOrigins,site-per-process')
                options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                
                self.driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)
                # Additional anti-detection
                try:
                    self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                        'source': '''
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            });
                        '''
                    })
                except:
                    pass
                print("✅ Browser driver initialized (undetected-chromedriver locally)")
            
            # Additional anti-detection
            try:
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                    '''
                })
            except:
                pass  # CDP might not be available in all setups
            
            print("✅ Browser driver initialized")
        except Exception as e:
            print(f"❌ Error setting up Chrome driver: {e}")
            print("Make sure Chrome/Chromium is installed")
            if is_docker:
                print("Docker tip: Make sure Chromium is installed in the Docker image")
            raise
    
    def fetch_product_page(self, url: str) -> Optional[str]:
        """Fetch the HTML content using undetected Chrome."""
        if not self.driver:
            self._setup_driver()
        
        try:
            step_start = time.time()
            print(f"🌐 Loading page with browser...")
            # Set page load timeout
            self.driver.set_page_load_timeout(60)
            try:
                self.driver.get(url)
            except Exception as e:
                print(f"⚠️  Page load timeout or error: {e}")
                print("  Continuing with current page state...")
            step_end = time.time()
            print(f"  ⏱️  Page load: {step_end - step_start:.2f}s")
            
            step_start = time.time()
            print("  Checking for modals...")
            # Check for geolocation modal immediately and dismiss it fast
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                # Look for geolocation modal immediately (no wait)
                try:
                    stay_button = WebDriverWait(self.driver, 1).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-qa-action="stay-in-store"]'))
                    )
                    print("  🌍 Geolocation modal detected, dismissing immediately...")
                    self.driver.execute_script("arguments[0].click();", stay_button)
                    print("  ✅ Dismissed geolocation modal")
                    time.sleep(0.5)  # Minimal wait after click
                except:
                    # Fallback: try close button
                    try:
                        close_button = WebDriverWait(self.driver, 0.5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.zds-dialog-close-button'))
                        )
                        print("  🌍 Geolocation modal detected, closing...")
                        self.driver.execute_script("arguments[0].click();", close_button)
                        print("  ✅ Closed geolocation modal")
                        time.sleep(0.5)
                    except:
                        pass
            except Exception as e:
                pass  # No modal, continue
            step_end = time.time()
            print(f"  ⏱️  Modal check/dismiss: {step_end - step_start:.2f}s")
            
            step_start = time.time()
            # Wait for JavaScript and bot protection to resolve (reduced time)
            time.sleep(2)  # Reduced from 3 seconds
            step_end = time.time()
            print(f"  ⏱️  Wait for JS/bot protection: {step_end - step_start:.2f}s")
            
            step_start = time.time()
            # Simulate human-like behavior: scroll a bit (faster)
            self.driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(0.3)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.3)
            step_end = time.time()
            print(f"  ⏱️  Scroll simulation: {step_end - step_start:.2f}s")
            
            # Wait for specific elements that indicate the page loaded
            step_start = time.time()
            print("  Checking page content...")
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                # Wait for product page elements (with shorter timeout)
                WebDriverWait(self.driver, 5).until(
                    lambda d: 'product' in d.current_url.lower() or 
                             d.find_elements(By.CLASS_NAME, 'product-detail') or
                             d.find_elements(By.CLASS_NAME, 'size-selector') or
                             'ZW COLLECTION' in d.page_source or
                             'WOOL BLEND' in d.page_source
                )
                print("  ✅ Product page detected")
            except Exception as e:
                if self.verbose:
                    print(f"  ⚠️  Wait timeout: {e}, continuing anyway...")
                pass  # Continue even if wait times out
            step_end = time.time()
            print(f"  ⏱️  Page content check: {step_end - step_start:.2f}s")
            
            # Quick check: Is the item out of stock? (speed optimization)
            step_start = time.time()
            print("  Checking stock status...")
            try:
                from selenium.webdriver.common.by import By
                # Look for "OUT OF STOCK" button - this means we can skip clicking size selector
                try:
                    out_of_stock_button = self.driver.find_element(
                        By.XPATH, 
                        "//button[contains(., 'OUT OF STOCK')]"
                    )
                    if out_of_stock_button:
                        print(f"  ❌ Item is OUT OF STOCK (detected early, skipping size selector click)")
                        step_end = time.time()
                        print(f"  ⏱️  Stock status check: {step_end - step_start:.2f}s")
                        # Return page source - parser will detect it's out of stock
                        return self.driver.page_source
                except:
                    # Button not found, item might be in stock, continue
                    pass
            except Exception as e:
                if self.verbose:
                    print(f"  (Stock check error: {e}, continuing...)")
            step_end = time.time()
            print(f"  ⏱️  Stock status check: {step_end - step_start:.2f}s")
            
            # Try to click "Select a size" button to open the size selector popup
            step_start = time.time()
            print("  Looking for size selector button...")
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                # Look for the "Select a size" or "Add to cart" button
                size_button_selectors = [
                    (By.XPATH, "//button[contains(text(), 'Select a size')]"),
                    (By.XPATH, "//button[contains(@aria-label, 'Select a size')]"),
                    (By.CSS_SELECTOR, "button[data-qa-action='add-to-cart']"),
                    (By.CSS_SELECTOR, "button.product-detail-cart-buttons__button"),
                ]
                
                button_found = False
                for selector_type, selector in size_button_selectors:
                    try:
                        button = WebDriverWait(self.driver, 2).until(
                            EC.element_to_be_clickable((selector_type, selector))
                        )
                        print("  ✅ Found size button, clicking to open popup...")
                        self.driver.execute_script("arguments[0].click();", button)
                        time.sleep(1.5)  # Wait for popup to open (reduced from 2s)
                        button_found = True
                        break
                    except:
                        continue
                
                if not button_found:
                    print("  ⚠️  Size button not found, sizes may be in page HTML already")
            except Exception as e:
                if self.verbose:
                    print(f"  Could not click size button: {e}")
            step_end = time.time()
            print(f"  ⏱️  Size button click: {step_end - step_start:.2f}s")
            
            # Additional wait for dynamic content
            step_start = time.time()
            print("  Getting page source...")
            time.sleep(0.5)  # Reduced from 1s
            
            # Check if we're still on bot protection page
            page_source = self.driver.page_source
            step_end = time.time()
            print(f"  ⏱️  Get page source: {step_end - step_start:.2f}s (length: {len(page_source)} chars)")
            
            # Check for bot protection - be more lenient
            is_blocked = (
                len(page_source) < 500 or 
                'Access Denied' in page_source or 
                (hasattr(self, '_is_bot_protection_page') and self._is_bot_protection_page(page_source)) or
                'Please enable JavaScript' in page_source or
                'challenge' in page_source.lower()
            )
            
            if is_blocked:
                print("⏳ Bot protection detected, trying anti-detection strategies...")
                
                # Try multiple anti-detection strategies
                for attempt in range(3):
                    wait_time = 3 + attempt * 2  # Progressive wait: 3s, 5s, 7s
                    print(f"  Attempt {attempt + 1}/3: waiting {wait_time}s...")
                    time.sleep(wait_time)
                    
                    # Human-like scrolling pattern
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
                    time.sleep(1)
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 2/3);")
                    time.sleep(1)
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    
                    # Try clicking somewhere to show human interaction
                    try:
                        body = self.driver.find_element('tag name', 'body')
                        self.driver.execute_script("arguments[0].click();", body)
                    except:
                        pass
                    
                    time.sleep(2)
                    page_source = self.driver.page_source
                    
                    # Check if we got past the protection
                    if len(page_source) > 1000 and 'Access Denied' not in page_source:
                        print(f"  ✅ Bot protection bypassed after {attempt + 1} attempt(s)")
                        break
                
                if len(page_source) < 500 or 'Access Denied' in page_source:
                    print("⚠️  Still seeing bot protection - page may be blocked.")
                    print(f"  Page length: {len(page_source)} chars")
                    if not self.headless:
                        print("   Browser window is open - you may need to manually complete the challenge.")
                        try:
                            input("Press Enter after completing any challenges (or Ctrl+C to skip)...")
                            page_source = self.driver.page_source
                        except KeyboardInterrupt:
                            print("   Skipping manual challenge...")
            
            return page_source
        except Exception as e:
            print(f"❌ Error fetching {url} with browser: {e}")
            return None
    
    def check_stock(self, url: str) -> Dict:
        """Check stock for a single product URL."""
        total_start = time.time()
        print(f"Checking stock for: {url}")
        html = self.fetch_product_page(url)
        
        if not html:
            return {
                'url': url,
                'error': 'Failed to fetch page',
                'in_stock': False
            }
        
        step_start = time.time()
        print("  Parsing HTML for stock info...")
        stock_info = self.parse_stock_info(html, url)
        step_end = time.time()
        print(f"  ⏱️  HTML parsing: {step_end - step_start:.2f}s")
        
        total_end = time.time()
        print(f"⏱️  TOTAL TIME: {total_end - total_start:.2f}s")
        return stock_info
    
    def monitor_products(self):
        """Continuously monitor all products in the config."""
        products = self.config.get('products', [])
        if not products:
            print("No products configured. Add URLs to config.json")
            return
        
        print(f"Monitoring {len(products)} product(s)...")
        print(f"Check interval: {self.config.get('check_interval', 300)} seconds\n")
        
        last_notified = {}  # Track last notification time per URL
        
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
                    last_in_stock = last_state.get('in_stock')
                    last_notify_time = last_state.get('time', 0)
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
    
    def __del__(self):
        """Cleanup: close the driver."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


def main():
    """Main entry point."""
    if not UC_AVAILABLE:
        print("Please install undetected-chromedriver:")
        print("  pip install undetected-chromedriver")
        sys.exit(1)
    
    verbose = '-v' in sys.argv or '--verbose' in sys.argv
    if verbose:
        sys.argv = [arg for arg in sys.argv if arg not in ['-v', '--verbose']]
    
    # Detect if running in Docker (no DISPLAY available)
    import os
    is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
    
    # In Docker, use headless (no display available)
    # Locally, default to non-headless (better for bypassing bot protection)
    if is_docker:
        headless = '--no-headless' not in sys.argv  # Default to headless in Docker
        if '--no-headless' in sys.argv:
            sys.argv.remove('--no-headless')
        if '--headless' in sys.argv:
            sys.argv.remove('--headless')
    else:
        # Local: default to non-headless
        headless = '--headless' in sys.argv
        if '--headless' in sys.argv:
            sys.argv.remove('--headless')
        if '--no-headless' in sys.argv:
            headless = False
            sys.argv.remove('--no-headless')
    
    checker = ZaraStockCheckerBrowser(verbose=verbose, headless=headless)
    
    # If URL provided as command line argument, check it once
    if len(sys.argv) > 1:
        url = sys.argv[1]
        stock_info = checker.check_stock(url)
        
        print("\n" + "="*60)
        print("STOCK CHECK RESULT")
        print("="*60)
        print(json.dumps(stock_info, indent=2))
        print("="*60)
        
        # HTML saving removed for speed optimization
        
        if stock_info.get('in_stock'):
            print(f"\n🎉 SUCCESS! Found {len(stock_info['available_sizes'])} available sizes:")
            for size in stock_info['available_sizes']:
                print(f"   - {size}")
        else:
            print("\n❌ No available sizes detected")
        
        # Send notification for both in-stock and out-of-stock (for one-time checks)
        print("\n📤 Sending notification...")
        checker.send_notification(stock_info)
    else:
        # No URL provided - run continuous monitoring from config
        print("No URL provided, starting continuous monitoring from config.json...")
        checker.monitor_products()


if __name__ == "__main__":
    main()

