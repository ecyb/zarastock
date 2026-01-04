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
import atexit

# Import the parsing logic from the main checker
from zara_stock_checker import ZaraStockChecker

# Try to import Playwright for Browserless support
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class BrowserlessFetcher:
    """Fetcher using Playwright + Browserless for cloud deployments."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.pw = None
        self.browser = None

    def _connect(self):
        if self.browser:
            return
        
        # Check for BROWSERLESS_URL first (may include token), then fall back to BROWSERLESS_TOKEN
        ws = os.environ.get("BROWSERLESS_URL")
        if not ws:
            token = os.environ.get("BROWSERLESS_TOKEN")
            if not token:
                raise RuntimeError("Missing BROWSERLESS_TOKEN or BROWSERLESS_URL env var")
            # Default to UK region for Zara UK, with stealth (proxy optional)
            # Format: wss://production-lon.browserless.io?token=TOKEN&stealth=true
            use_proxy = os.environ.get("BROWSERLESS_USE_PROXY", "false").lower() == "true"
            if use_proxy:
                ws = f"wss://production-lon.browserless.io?token={token}&stealth=true&proxy=residential&proxyCountry=gb"
                if self.verbose:
                    print(f"  Using default UK region with residential proxy")
            else:
                ws = f"wss://production-lon.browserless.io?token={token}&stealth=true"
                if self.verbose:
                    print(f"  Using default UK region (set BROWSERLESS_USE_PROXY=true for residential proxy)")
        else:
            # If URL is provided, check if it needs proxy/stealth params
            # Only add if not already present
            # Note: Residential proxy might not be available on all plans, so make it optional
            use_proxy = os.environ.get("BROWSERLESS_USE_PROXY", "false").lower() == "true"
            if use_proxy and "proxy" not in ws.lower():
                separator = "&" if "?" in ws else "?"
                ws = f"{ws}{separator}proxy=residential&proxyCountry=gb"
                if self.verbose:
                    print(f"  Added residential proxy to URL (set BROWSERLESS_USE_PROXY=true to enable)")
            elif not use_proxy and self.verbose:
                print(f"  Skipping residential proxy (set BROWSERLESS_USE_PROXY=true to enable)")
            if "stealth" not in ws.lower():
                separator = "&" if "?" in ws else "?"
                ws = f"{ws}{separator}stealth=true"
                if self.verbose:
                    print(f"  Added stealth mode to URL")

        self.pw = sync_playwright().start()
        # Connect over CDP websocket with stealth mode and proxy enabled
        self.browser = self.pw.chromium.connect_over_cdp(ws)

        if self.verbose:
            print("✅ Connected to Browserless")

    def fetch_html(self, url: str, timeout_ms: int = 60000) -> Optional[str]:
        self._connect()

        # Use stealth mode and anti-detection features
        # Browserless should handle this, but we'll add extra stealth measures
        context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-GB",
            timezone_id="Europe/London",
            # Disable automation indicators
            java_script_enabled=True,
            # Add more realistic headers
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-GB,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
                "Referer": "https://www.google.com/",
            },
        )
        page = context.new_page()

        try:
            # Add stealth scripts to hide automation
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = {
                    runtime: {},
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-GB', 'en'],
                });
            """)

            if self.verbose:
                print(f"🌐 Browserless goto: {url}")

            # Skip homepage visit for now - it might be causing the browser to close
            # Navigate directly to product page
            html = None
            try:
                if self.verbose:
                    print(f"  Navigating to product page...")
                # Use domcontentloaded first (more reliable)
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                
                # CRITICAL: Capture HTML immediately after navigation, before any waits
                # This ensures we have HTML even if the page closes during waits
                try:
                    html = page.content()
                    if self.verbose and html:
                        print(f"  ✅ Captured HTML immediately ({len(html)} chars)")
                except Exception as e:
                    if "closed" in str(e).lower():
                        raise Exception("Page was closed immediately after navigation")
                    raise
                
                # Now try to wait for JS to execute and network to be idle
                # But if page closes, we already have HTML
                try:
                    page.wait_for_timeout(2000)
                    # Then wait for network to be idle (but with shorter timeout)
                    try:
                        page.wait_for_load_state("networkidle", timeout=20000)
                    except:
                        if self.verbose:
                            print("  ⚠️  Networkidle timeout, continuing anyway...")
                except Exception as wait_error:
                    if "closed" in str(wait_error).lower():
                        if self.verbose:
                            print("  ⚠️  Page closed during wait, using captured HTML")
                        if html and len(html) > 1000:
                            return html
                        raise Exception("Page closed during wait and we don't have valid HTML")
                    raise
                    
                # Try to get updated HTML after waits (in case JS loaded more content)
                if not page.is_closed():
                    try:
                        updated_html = page.content()
                        if updated_html and len(updated_html) > len(html or ""):
                            html = updated_html
                            if self.verbose:
                                print(f"  ✅ Got updated HTML ({len(html)} chars)")
                    except:
                        pass  # Use the HTML we already have
                        
            except Exception as nav_error:
                error_msg = str(nav_error).lower()
                if "closed" in error_msg or "target page" in error_msg:
                    # If we have HTML, return it; otherwise raise
                    if html and len(html) > 1000:
                        if self.verbose:
                            print(f"  ⚠️  Browser closed but we have HTML ({len(html)} chars)")
                        return html
                    raise Exception(f"Browser/context was closed during navigation. This might be due to: 1) Residential proxy not available on your plan, 2) Browserless connection issue, 3) Zara blocking the connection. Error: {nav_error}")
                raise
            
            # Ensure we have HTML before continuing
            if not html:
                raise Exception("Failed to capture HTML content")

            # Zara is JS-heavy; give it more time to render (but we already have HTML)
            try:
                page.wait_for_timeout(3000)  # Reduced wait time since we already have HTML
                # Try to get updated HTML after wait (in case JS loaded more content)
                if not page.is_closed():
                    try:
                        html = page.content()
                    except:
                        pass  # Use the HTML we already have
            except Exception as e:
                if "closed" in str(e).lower():
                    # Page closed during wait, but we already have HTML
                    if self.verbose:
                        print("  ⚠️  Page closed during wait, using previously captured HTML")
                    if html and len(html) > 1000:
                        return html
                    raise Exception("Page was closed and we don't have valid HTML content")
            
            if "Access Denied" in html or len(html) < 500:
                if self.verbose:
                    print("⚠️  Possible bot protection detected, trying stealth measures...")
                # Wait longer and try scrolling to simulate human behavior
                try:
                    page.wait_for_timeout(3000)
                    # Simulate mouse movement
                    page.mouse.move(100, 100)
                    page.wait_for_timeout(500)
                    page.mouse.move(200, 200)
                    page.wait_for_timeout(500)
                    page.evaluate("window.scrollTo(0, 300)")
                    page.wait_for_timeout(1000)
                    page.evaluate("window.scrollTo(0, 600)")
                    page.wait_for_timeout(1000)
                    page.evaluate("window.scrollTo(0, 0)")
                    page.wait_for_timeout(2000)
                    # Try clicking somewhere to show interaction
                    try:
                        page.mouse.click(200, 200)
                        page.wait_for_timeout(1000)
                    except:
                        pass
                    html = page.content()
                except Exception as e:
                    if "closed" in str(e).lower():
                        if self.verbose:
                            print("  ⚠️  Page closed during stealth measures, using existing HTML")
                        # Use the HTML we already have
                        pass
                    else:
                        raise

            # Try to wait for product page elements (non-fatal but important)
            try:
                if not page.is_closed():
                    # Wait for any product-related element
                    page.wait_for_selector("button, [data-qa-action], .product-detail, .size-selector, [class*='product'], [class*='Product'], h1", timeout=10000)
                    if self.verbose:
                        print("  ✅ Product page elements detected")
            except Exception as e:
                if "closed" in str(e).lower():
                    if self.verbose:
                        print("  ⚠️  Page closed while waiting for elements")
                elif self.verbose:
                    print("  ⚠️  Product page elements not found, continuing anyway...")

            # Get final HTML (check if page is still open)
            try:
                if page.is_closed():
                    # Page already closed, use HTML we captured earlier
                    if 'html' in locals() and html and len(html) > 1000:
                        if self.verbose:
                            print(f"✅ Got HTML ({len(html)} chars) [from earlier capture]")
                        return html
                    raise Exception("Page was closed and we don't have valid HTML content")
                html = page.content()
            except Exception as e:
                if "closed" in str(e).lower():
                    # Try to use HTML we already have
                    if 'html' in locals() and html and len(html) > 1000:
                        if self.verbose:
                            print(f"  ⚠️  Page closed, using previously captured HTML ({len(html)} chars)")
                        return html
                    raise Exception("Page was closed and we don't have HTML content")
                raise
            
            if self.verbose:
                print(f"✅ Got HTML ({len(html)} chars)")
                if "Access Denied" in html or len(html) < 1000:
                    print("⚠️  WARNING: Still getting 'Access Denied' or very short HTML")
                    print("   This likely means Zara is blocking Browserless IP addresses")
                    print("   Consider: 1) Using a different Browserless region/endpoint")
                    print("             2) Using Browserless with residential proxy (set BROWSERLESS_USE_PROXY=true)")
                    print("             3) Contacting Browserless support about IP blocking")
                    print(f"\n📄 ACTUAL HTML CONTENT ({len(html)} chars):")
                    print("=" * 80)
                    print(html)
                    print("=" * 80)
            return html

        except PWTimeoutError as e:
            if self.verbose:
                print(f"⚠️ Timeout: {e}")
            return page.content()

        finally:
            try:
                page.close()
                context.close()
            except:
                pass

    def close(self):
        try:
            if self.browser:
                self.browser.close()
        except:
            pass
        try:
            if self.pw:
                self.pw.stop()
        except:
            pass
        self.browser = None
        self.pw = None


class ZaraStockCheckerBrowser(ZaraStockChecker):
    """Zara stock checker using undetected-chromedriver to bypass bot protection."""
    
    def __init__(self, config_file: str = "config.json", verbose: bool = False, headless: bool = True):
        """Initialize with undetected Chrome webdriver or Browserless."""
        super().__init__(config_file, verbose)
        self.headless = headless
        self.driver = None
        self.browserless = None
        
        # Use Browserless if configured (for cloud deployments)
        # Check for either BROWSERLESS_URL or BROWSERLESS_TOKEN
        if os.environ.get("BROWSERLESS_URL") or os.environ.get("BROWSERLESS_TOKEN"):
            if not PLAYWRIGHT_AVAILABLE:
                raise ImportError("BROWSERLESS_URL/BROWSERLESS_TOKEN set but Playwright not installed. Install with: pip install playwright && playwright install chromium")
            self.browserless = BrowserlessFetcher(verbose=self.verbose)
            if self.verbose:
                print("✅ Using Browserless (cloud browser) - Selenium not used")
        else:
            # Only setup local Selenium if Browserless is not configured
            if not UC_AVAILABLE:
                raise ImportError("undetected-chromedriver is required. Install with: pip install undetected-chromedriver")
            self._setup_driver()
        
        # Register cleanup on exit (more reliable than __del__)
        atexit.register(self.cleanup)
    
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
                # Stable baseline for Railway
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--disable-setuid-sandbox')
                chrome_options.add_argument('--no-zygote')
                chrome_options.add_argument('--window-size=1920,1080')
                # Use unique user-data-dir per process to avoid profile locks
                chrome_options.add_argument(f'--user-data-dir=/tmp/chrome-data-{os.getpid()}')
                chrome_options.add_argument(f'--disk-cache-dir=/tmp/chrome-cache-{os.getpid()}')
                # CRITICAL: Disable renderer to prevent crashes in containers
                chrome_options.add_argument('--disable-software-rasterizer')
                chrome_options.add_argument('--disable-gpu-compositing')
                chrome_options.add_argument('--disable-accelerated-2d-canvas')
                # Additional aggressive flags to prevent crashes
                chrome_options.add_argument('--disable-features=VizDisplayCompositor')
                chrome_options.add_argument('--disable-ipc-flooding-protection')
                chrome_options.add_argument('--disable-background-networking')
                chrome_options.add_argument('--disable-background-timer-throttling')
                chrome_options.add_argument('--disable-renderer-backgrounding')
                chrome_options.add_argument('--disable-backgrounding-occluded-windows')
                chrome_options.add_argument('--disable-breakpad')
                chrome_options.add_argument('--disable-client-side-phishing-detection')
                chrome_options.add_argument('--disable-component-update')
                chrome_options.add_argument('--disable-default-apps')
                chrome_options.add_argument('--disable-extensions')
                chrome_options.add_argument('--disable-hang-monitor')
                chrome_options.add_argument('--disable-popup-blocking')
                chrome_options.add_argument('--disable-prompt-on-repost')
                chrome_options.add_argument('--disable-sync')
                chrome_options.add_argument('--disable-translate')
                chrome_options.add_argument('--disable-web-resources')
                chrome_options.add_argument('--metrics-recording-only')
                chrome_options.add_argument('--no-first-run')
                chrome_options.add_argument('--safebrowsing-disable-auto-update')
                chrome_options.add_argument('--enable-automation')
                chrome_options.add_argument('--password-store=basic')
                chrome_options.add_argument('--use-mock-keychain')
                # Cap V8 memory to prevent OOM on heavy JS pages like Zara
                chrome_options.add_argument('--js-flags=--max-old-space-size=128')
                # Chrome logging for debugging crashes
                chrome_options.add_argument('--enable-logging=stderr')
                chrome_options.add_argument('--v=1')
                chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                # Don't exclude 'enable-logging' - we want logging enabled!
                chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
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
                    # Don't set log_output - ChromeDriver will log to stderr (which we already capture)
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
    
    def _ensure_driver_valid(self, skip_check: bool = False):
        """Check if driver is valid, recreate if window is closed or DevTools disconnected.
        
        Args:
            skip_check: If True, skip the validity check and always recreate the driver (used when we know driver is dead).
        """
        if not self.driver:
            self._setup_driver()
            return
        
        if skip_check:
            # Skip check and just recreate (used when we know driver is dead)
            print("⚠️  Recreating driver (skip_check=True)...")
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
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
                # Only recreate on dead driver errors - don't recreate for other errors
                raise
    
    def _safe(self, fn, *args, **kwargs):
        """
        Execute a driver operation safely, retrying with fresh driver if driver is dead.
        
        Args:
            fn: Function that accepts (driver, *args, **kwargs). This guarantees we always
                use the current self.driver after restart.
        """
        for attempt in range(2):
            # On second attempt, skip check since we know driver is dead
            self._ensure_driver_valid(skip_check=(attempt == 1))
            try:
                return fn(self.driver, *args, **kwargs)
            except Exception as e:
                if self._is_dead_driver_error(e) and attempt == 0:
                    print("⚠️  Driver died mid-op. Recreating...")
                    continue
                raise
    
    def fetch_product_page(self, url: str, retry: bool = True) -> Optional[str]:
        """Fetch the HTML content using browser automation."""
        # Prefer Browserless if configured (for cloud deployments)
        if self.browserless:
            try:
                return self.browserless.fetch_html(url)
            except Exception as e:
                print(f"❌ Browserless error: {e}")
                return None
        
        # Otherwise, use local Selenium/undetected-chromedriver
        try:
            print(f"🌐 Loading page with browser...")
            self._safe(lambda d: d.set_page_load_timeout(60))
            
            # Try to load the page
            try:
                self._safe(lambda d, u: d.get(u), url)
                print("  ✅ Page load initiated")
            except Exception as load_error:
                if self._is_dead_driver_error(load_error):
                    print(f"  ❌ Driver died during page load: {load_error}")
                    if retry:
                        print("  ⚠️  Retrying with fresh driver...")
                        self._ensure_driver_valid(skip_check=True)
                        return self.fetch_product_page(url, retry=False)
                    raise
                raise
            
            # Wait for page to render (longer wait for heavy JS pages)
            print("  ⏳ Waiting for page to render...")
            time.sleep(5)  # Increased from 2s to 5s for heavy JS pages
            
            # Get page source
            try:
                page_source = self._safe(lambda d: d.page_source)
                print(f"  ✅ Got page source ({len(page_source) if page_source else 0} chars)")
            except Exception as source_error:
                if self._is_dead_driver_error(source_error):
                    print(f"  ❌ Driver died while getting page source: {source_error}")
                    if retry:
                        print("  ⚠️  Retrying with fresh driver...")
                        self._ensure_driver_valid(skip_check=True)
                        return self.fetch_product_page(url, retry=False)
                    raise
                raise

            if not page_source or len(page_source) < 100:
                raise Exception(f"Page source is empty or too short ({len(page_source) if page_source else 0} chars)")

            print(f"✅ Got page source ({len(page_source)} chars)")
            return page_source

        except Exception as e:
            if retry and self._is_dead_driver_error(e):
                print("⚠️  Browser died. Recreating and retrying once...")
                self._ensure_driver_valid(skip_check=True)
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
    
    def cleanup(self):
        """Cleanup: close browser (called by atexit, more reliable than __del__)."""
        # Close Browserless connection if used
        if hasattr(self, 'browserless') and self.browserless:
            try:
                self.browserless.close()
            except:
                pass
        
        # Close local Selenium driver if used
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def __del__(self):
        """Cleanup: close the driver (fallback, but atexit is more reliable)."""
        self.cleanup()


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

