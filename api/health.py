import json

def handler(request):
    """Vercel serverless function for /api/health"""
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'status': 'ok',
            'service': 'zara-stock-checker'
        })
    }

