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
import shutil
import glob

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
        """Setup undetected Chrome WebDriver (local) or regular Selenium (Docker/Railway)."""
        try:
            import os
            # Detect Docker or Railway (both should use regular Selenium)
            is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
            is_railway = os.environ.get('RAILWAY_ENVIRONMENT') is not None or os.environ.get('RAILWAY_PROJECT_ID') is not None
            is_cloud = is_docker or is_railway
            
            # In Docker/Railway, use regular Selenium (more stable, headless anyway)
            if is_cloud:
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from selenium.webdriver.chrome.options import Options
                
                chrome_options = Options()
                # Bare minimum set for Railway stability
                chrome_options.add_argument('--headless')  # Use classic headless, not --headless=new
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--remote-debugging-port=9222')
                chrome_options.add_argument('--window-size=1920,1080')
                chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                # Find Chromium binary (check Nix store paths for Railway)
                chrome_binaries = [
                    '/usr/bin/chromium',
                    '/usr/bin/chromium-browser',
                    '/usr/bin/google-chrome-stable',
                    '/usr/bin/google-chrome',
                    '/nix/store/*/bin/chromium',  # Nix store path (Railway)
                    '/run/current-system/sw/bin/chromium',  # NixOS path
                ]
                
                # Also try to find via which command
                chromium_which = shutil.which('chromium') or shutil.which('chromium-browser')
                if chromium_which and chromium_which not in chrome_binaries:
                    chrome_binaries.insert(0, chromium_which)
                
                chrome_bin = None
                for bin_path in chrome_binaries:
                    # Handle glob patterns for Nix store
                    if '*' in bin_path:
                        matches = glob.glob(bin_path)
                        if matches:
                            bin_path = matches[0]
                    
                    if os.path.exists(bin_path):
                        chrome_bin = bin_path
                        chrome_options.binary_location = bin_path
                        if self.verbose:
                            print(f"  Using browser: {bin_path}")
                        break
                
                if not chrome_bin:
                    # Last resort: try to find via which
                    chromium_which = shutil.which('chromium') or shutil.which('chromium-browser')
                    if chromium_which:
                        chrome_bin = chromium_which
                        chrome_options.binary_location = chromium_which
                        if self.verbose:
                            print(f"  Using browser (via which): {chromium_which}")
                
                # Find ChromeDriver
                chromedriver_path = shutil.which('chromedriver') or '/usr/bin/chromedriver'
                
                # Check Nix store for chromedriver
                if not os.path.exists(chromedriver_path):
                    import glob
                    nix_chromedriver = glob.glob('/nix/store/*/bin/chromedriver')
                    if nix_chromedriver:
                        chromedriver_path = nix_chromedriver[0]
                
                if os.path.exists(chromedriver_path):
                    service = Service(chromedriver_path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    if self.verbose:
                        print(f"  Using ChromeDriver: {chromedriver_path}")
                else:
                    # Let Selenium auto-detect (will use system chromedriver)
                    if self.verbose:
                        print("  ChromeDriver not found at expected path, using auto-detection")
                    self.driver = webdriver.Chrome(options=chrome_options)
                
                env_name = "Railway" if is_railway else "Docker"
                print(f"✅ Browser driver initialized (Selenium on {env_name})")
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
            if is_cloud:
                env_name = "Railway" if is_railway else "Docker"
                print(f"{env_name} tip: Make sure Chromium is installed in the build configuration")
            raise
    
    def _is_dead_driver_error(self, e: Exception) -> bool:
        """Check if error indicates driver is dead (window closed or DevTools disconnected)."""
        msg = str(e).lower()
        return any(x in msg for x in [
            "no such window",
            "target window already closed",
            "web view not found",
            "disconnected",
            "not connected to devtools",
            "devtools"
        ])
    
    def _ensure_driver_valid(self):
        """Check if driver is valid, recreate if window is closed or DevTools disconnected."""
        if not self.driver:
            self._setup_driver()
            return
        
        try:
            # Try to get current window handle to check if driver is still valid
            _ = self.driver.current_window_handle
        except Exception as e:
            # Driver is invalid (window closed or DevTools disconnected), recreate it
            if self._is_dead_driver_error(e):
                print("⚠️  Driver is dead (window/DevTools). Recreating...")
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
                self._setup_driver()
            else:
                raise
    
    def _safe_driver_operation(self, operation, *args, **kwargs):
        """Execute a driver operation, retrying with fresh driver if driver is dead."""
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            if self._is_dead_driver_error(e):
                print("⚠️  Driver died mid-operation. Recreating and retrying once...")
                self._ensure_driver_valid()
                # Retry the operation
                return operation(*args, **kwargs)
            else:
                raise
    
    def fetch_product_page(self, url: str, retry: bool = True) -> Optional[str]:
        """Fetch the HTML content using browser automation."""
        try:
            self._ensure_driver_valid()
            
            # Use _safe_driver_operation for all driver calls
            print(f"🌐 Loading page with browser...")
            self._safe_driver_operation(self.driver.set_page_load_timeout, 60)
            self._safe_driver_operation(self.driver.get, url)
            
            # Wait for page to render
            time.sleep(2)
            
            # Get page source - if DevTools disconnects, _safe_driver_operation will recreate driver and retry
            page_source = self._safe_driver_operation(lambda: self.driver.page_source)
            
            if not page_source or len(page_source) < 100:
                raise Exception("Page source is empty or too short")
            
            print(f"✅ Got page source ({len(page_source)} chars)")
            return page_source
            
        except Exception as e:
            # If driver died, recreate and retry once
            if retry and self._is_dead_driver_error(e):
                print("⚠️  Browser died. Restarting and retrying once...")
                try:
                    if self.driver:
                        self.driver.quit()
                except:
                    pass
                self.driver = None
                self._setup_driver()
                return self.fetch_product_page(url, retry=False)
            
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

