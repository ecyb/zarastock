#!/usr/bin/env python3
"""
Simple API server for Zara Stock Checker
Can be called via HTTP requests (e.g., from cron jobs)
"""

from flask import Flask, jsonify, request
import os
import sys

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
            checker = ZaraStockCheckerBrowser(verbose=False, headless=True)
            print("✅ Using browser-based checker (undetected-chromedriver)")
        except ImportError:
            # Fallback to non-browser version (may be blocked by bot protection)
            try:
                from zara_stock_checker import ZaraStockChecker
                checker = ZaraStockChecker(verbose=False)
                print("⚠️  Using non-browser checker (may be blocked by bot protection)")
            except Exception as e:
                raise Exception(f"Failed to initialize any stock checker: {str(e)}")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error initializing browser checker: {e}")
            print(f"Traceback: {error_details}")
            # Try fallback
            try:
                from zara_stock_checker import ZaraStockChecker
                checker = ZaraStockChecker(verbose=False)
                print("⚠️  Fallback to non-browser checker")
            except Exception as e2:
                raise Exception(f"Failed to initialize stock checker: {str(e)}. Browser automation not available in this environment.")
    return checker

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'message': 'Zara Stock Checker API is running'})

@app.route('/check', methods=['POST', 'GET'])
def check_stock():
    """Check stock for all products in config."""
    try:
        checker_instance = get_checker()
        
        # Get products from config
        products = checker_instance.config.get('products', [])
        if not products:
            return jsonify({
                'error': 'No products configured',
                'status': 'error'
            }), 400
        
        results = []
        for product_url in products:
            try:
                stock_info = checker_instance.check_stock(product_url)
                results.append({
                    'url': stock_info.get('url'),
                    'name': stock_info.get('name'),
                    'price': stock_info.get('price'),
                    'in_stock': stock_info.get('in_stock', False),
                    'available_sizes': stock_info.get('available_sizes', []),
                    'timestamp': stock_info.get('timestamp')
                })
            except Exception as e:
                results.append({
                    'url': product_url,
                    'error': str(e),
                    'status': 'error'
                })
        
        return jsonify({
            'status': 'success',
            'results': results,
            'count': len(results)
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
        
        return jsonify({
            'status': 'success',
            'url': stock_info.get('url'),
            'name': stock_info.get('name'),
            'price': stock_info.get('price'),
            'in_stock': stock_info.get('in_stock', False),
            'available_sizes': stock_info.get('available_sizes', []),
            'timestamp': stock_info.get('timestamp')
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

# Export app for Vercel
# Vercel will automatically detect the 'app' variable

if __name__ == '__main__':
    # Railway and other platforms set PORT env var
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"🚀 Starting Zara Stock Checker API server on {host}:{port}")
    print(f"📡 Endpoints:")
    print(f"   GET/POST /health - Health check")
    print(f"   GET/POST /check - Check all products from config")
    print(f"   GET/POST /check/<url> - Check single product")
    print(f"\n💡 Example cron job:")
    print(f"   curl http://localhost:{port}/check")
    
    app.run(host=host, port=port, debug=False)

