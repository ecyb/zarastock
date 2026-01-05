import json
import os
import sys
from http.server import BaseHTTPRequestHandler

# Add parent directory to path to import run_and_notify
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from run_and_notify import ZaraStockChecker
except Exception as e:
    print(f"Error importing ZaraStockChecker: {e}")
    import traceback
    traceback.print_exc()
    ZaraStockChecker = None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        return self.handle_request()
    
    def do_POST(self):
        return self.handle_request()
    
    def handle_request(self):
        """Vercel serverless function for /api/stock-check"""
        try:
            if ZaraStockChecker is None:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Failed to import ZaraStockChecker',
                    'status': 'error'
                }).encode())
                return
            
            # Get products from environment or config
            checker = ZaraStockChecker(verbose=False)
            
            products = checker.config.get('products', [])
            if not products:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'No products configured',
                    'status': 'error'
                }).encode())
                return
            
            results = []
            notifications_sent = set()
            
            for product_url in products:
                try:
                    stock_info = checker.check_stock(product_url)
                    
                    current_in_stock = stock_info.get('in_stock', False)
                    skip_nostock = checker.config.get('skip_nostock_notification', False)
                    
                    # Send notification if in stock or if not skipping out-of-stock notifications
                    if current_in_stock or (not current_in_stock and not skip_nostock):
                        try:
                            checker.send_notification(stock_info)
                            notifications_sent.add(product_url)
                        except Exception as e:
                            print(f"Error sending notification: {e}")
                    
                    results.append({
                        'url': stock_info.get('url', product_url),
                        'requested_url': product_url,
                        'name': stock_info.get('name'),
                        'price': stock_info.get('price'),
                        'in_stock': stock_info.get('in_stock', False),
                        'available_sizes': stock_info.get('available_sizes', []),
                        'method': stock_info.get('method', 'api'),
                        'timestamp': stock_info.get('timestamp'),
                        'notification_sent': product_url in notifications_sent,
                        'error': stock_info.get('error'),
                    })
                except Exception as e:
                    import traceback
                    error_trace = traceback.format_exc()
                    print(f"Error checking {product_url}: {e}")
                    print(error_trace)
                    results.append({
                        'url': product_url,
                        'error': str(e),
                        'status': 'error',
                    })
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'success',
                'results': results,
                'count': len(results),
                'notifications_sent': len(notifications_sent),
                'checker_type': 'api'
            }).encode())
        
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error in check handler: {e}")
            print(error_trace)
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': str(e),
                'status': 'error',
                'traceback': error_trace
            }).encode())

