#!/usr/bin/env python3
"""
Simple API server for Zara Stock Checker
Can be called via HTTP requests (e.g., from cron jobs)
"""

from flask import Flask, jsonify, request
import os
import sys
import argparse

app = Flask(__name__)

# Global checker instance
checker = None

def get_checker():
    """Get or create checker instance."""
    global checker
    if checker is None:
        # Try browser version first (better bot protection bypass)
        try:
            from zara_stock_checker_browser import ZaraStockCheckerBrowser
            checker = ZaraStockCheckerBrowser(verbose=True, headless=True)  # Enable verbose for Railway debugging
            print("✅ Using browser-based checker (undetected-chromedriver)")
        except ImportError as import_err:
            # Fallback to non-browser version (may be blocked by bot protection)
            print(f"⚠️  Browser checker not available (ImportError: {import_err})")
            try:
                from zara_stock_checker import ZaraStockChecker
                checker = ZaraStockChecker(verbose=True)  # Enable verbose for Railway debugging
                print("⚠️  Using non-browser checker (may be blocked by bot protection)")
            except Exception as e:
                raise Exception(f"Failed to initialize any stock checker: {str(e)}")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Error initializing browser checker: {e}")
            print(f"Traceback: {error_details}")
            # Try fallback
            try:
                from zara_stock_checker import ZaraStockChecker
                checker = ZaraStockChecker(verbose=True)  # Enable verbose for Railway debugging
                print("⚠️  Fallback to non-browser checker (browser automation failed)")
            except Exception as e2:
                raise Exception(f"Failed to initialize stock checker: {str(e)}. Browser automation not available in this environment.")
    return checker

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'message': 'Zara Stock Checker API is running'})

@app.route('/check', methods=['POST', 'GET'])
def check_stock():
    """Check stock for all products in config, or a single URL if provided."""
    try:
        checker_instance = get_checker()
        
        # Check if a URL was passed as query parameter or in POST data
        url_param = request.args.get('url') or request.form.get('url') or request.json.get('url') if request.is_json else None
        
        # If URL is provided, use only that URL and ignore config
        if url_param:
            products = [url_param]
        else:
            # Get products from config
            products = checker_instance.config.get('products', [])
            if not products:
                return jsonify({
                    'error': 'No products configured and no URL provided',
                    'status': 'error',
                    'hint': 'Provide a URL via ?url=<product_url> or configure products in config.json/ZARA_PRODUCTS'
                }), 400
        
        # Get skip_nostock_notification setting (default: false - send all notifications)
        skip_nostock = checker_instance.config.get('skip_nostock_notification', False)
        
        results = []
        notifications_sent = []
        
        for product_url in products:
            try:
                stock_info = checker_instance.check_stock(product_url)
                
                # Check if parsing failed (null values indicate failure)
                if not stock_info.get('name') and not stock_info.get('error'):
                    # Add debug info if name/price are null
                    stock_info['error'] = 'Failed to parse product information - page may be blocked or HTML structure changed'
                    stock_info['debug'] = {
                        'url_fetched': bool(stock_info.get('url')),
                        'has_timestamp': bool(stock_info.get('timestamp')),
                        'in_stock': stock_info.get('in_stock', False)
                    }
                
                # Send notification every time (cron job behavior)
                # But skip if skip_nostock_notification is true and item is out of stock
                url = stock_info.get('url', product_url)
                current_in_stock = stock_info.get('in_stock', False)
                should_send = True
                
                if skip_nostock and not current_in_stock:
                    # Skip notification if item is out of stock and skip_nostock_notification is true
                    should_send = False
                
                if should_send:
                    try:
                        checker_instance.send_notification(stock_info)
                        notifications_sent.append(url)
                    except Exception as notify_error:
                        print(f"⚠️  Failed to send notification for {url}: {notify_error}")
                
                results.append({
                    'url': stock_info.get('url'),
                    'name': stock_info.get('name'),
                    'price': stock_info.get('price'),
                    'in_stock': stock_info.get('in_stock', False),
                    'available_sizes': stock_info.get('available_sizes', []),
                    'timestamp': stock_info.get('timestamp'),
                    'notification_sent': url in notifications_sent,
                    'error': stock_info.get('error'),
                    'debug': stock_info.get('debug')
                })
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                print(f"❌ Error checking {product_url}: {e}")
                print(f"Traceback: {error_trace}")
                results.append({
                    'url': product_url,
                    'error': str(e),
                    'status': 'error',
                    'traceback': error_trace if checker_instance.verbose else None
                })
        
        # Determine which checker is being used
        try:
            from zara_stock_checker_browser import ZaraStockCheckerBrowser
            checker_type = 'browser' if isinstance(checker_instance, ZaraStockCheckerBrowser) else 'non-browser'
        except ImportError:
            checker_type = 'non-browser'
        
        return jsonify({
            'status': 'success',
            'results': results,
            'count': len(results),
            'notifications_sent': len(notifications_sent),
            'checker_type': checker_type
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/check/<path:url>', methods=['POST', 'GET'])
def check_single(url):
    """Check stock for a single product URL."""
    try:
        # Decode URL if needed
        if not url.startswith('http'):
            from urllib.parse import unquote
            url = unquote(url)
        
        checker_instance = get_checker()
        
        stock_info = checker_instance.check_stock(url)
        
        # Get skip_nostock_notification setting (default: false - send all notifications)
        skip_nostock = checker_instance.config.get('skip_nostock_notification', False)
        
        # Send notification every time (cron job behavior)
        # But skip if skip_nostock_notification is true and item is out of stock
        product_url = stock_info.get('url', url)
        current_in_stock = stock_info.get('in_stock', False)
        should_send = True
        
        if skip_nostock and not current_in_stock:
            # Skip notification if item is out of stock and skip_nostock_notification is true
            should_send = False
        
        notification_sent = False
        if should_send:
            try:
                checker_instance.send_notification(stock_info)
                notification_sent = True
            except Exception as notify_error:
                print(f"⚠️  Failed to send notification for {product_url}: {notify_error}")
        
        return jsonify({
            'status': 'success',
            'url': stock_info.get('url'),
            'name': stock_info.get('name'),
            'price': stock_info.get('price'),
            'in_stock': stock_info.get('in_stock', False),
            'available_sizes': stock_info.get('available_sizes', []),
            'timestamp': stock_info.get('timestamp'),
            'notification_sent': notification_sent
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

# Export app for Vercel
# Vercel will automatically detect the 'app' variable

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Zara Stock Checker API Server')
    parser.add_argument('--port', '-p', type=int, default=None,
                        help='Port to run the server on (default: 5000 or PORT env var)')
    parser.add_argument('--host', type=str, default=None,
                        help='Host to bind to (default: 0.0.0.0 or HOST env var)')
    args = parser.parse_args()
    
    # Railway and other platforms set PORT env var
    # Command-line argument takes precedence over env var
    port = args.port if args.port is not None else int(os.environ.get('PORT', 5000))
    host = args.host if args.host is not None else os.environ.get('HOST', '0.0.0.0')
    
    print(f"🚀 Starting Zara Stock Checker API server on {host}:{port}")
    print(f"📡 Endpoints:")
    print(f"   GET/POST /health - Health check")
    print(f"   GET/POST /check - Check all products from config")
    print(f"   GET/POST /check?url=<product_url> - Check single product (ignores config)")
    print(f"   GET/POST /check/<url> - Check single product (alternative)")
    print(f"\n💡 Example cron job:")
    print(f"   curl http://localhost:{port}/check")
    print(f"   curl http://localhost:{port}/check?url=https://www.zara.com/uk/en/product.html")
    
    app.run(host=host, port=port, debug=False)

