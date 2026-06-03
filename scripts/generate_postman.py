import re
import json

URLS_PY = 'filemanager/urls.py'
OUT = 'postman_collection.json'

pattern = re.compile(r"path\(\s*'([^']*)'\s*,")

items = []

with open(URLS_PY, 'r', encoding='utf-8') as f:
    content = f.read()

matches = pattern.findall(content)
for m in matches:
    # skip empty root
    url = '/' + m if not m.startswith('/') else m
    # Skip API token and admin urls if present
    if url.startswith('/api/') or url.startswith('/admin'):
        continue
    # Create a basic GET request entry
    items.append({
        'name': url,
        'request': {
            'method': 'GET',
            'header': [],
            'url': {
                'raw': '{{base_url}}' + url,
                'host': ['{{base_url}}'],
                'path': [p for p in url.split('/') if p],
            }
        }
    })

collection = {
    'info': {
        'name': 'SecureDesk Tracker API (auto-generated)',
        'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'
    },
    'item': items
}

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(collection, f, indent=2)

print('postman_collection.json created with %d endpoints' % len(items))
