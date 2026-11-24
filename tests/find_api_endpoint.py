import requests
import json

# Let's see what endpoint /voting/cast uses by inspecting the page requests
r = requests.get('https://innovatecg.in/voting')
print("Page status:", r.status_code)

# Check if there is an API proxy under /api or a separate backend URL
import re
api_matches = re.findall(r'https?://[a-zA-Z0-9.-]+/(?:api|voting)[^\s"\'`]*', r.text)
print("API matches in HTML:", set(api_matches))

# Search in the JS bundles for the base URL of t.default (axios or fetch wrapper)
js_urls = re.findall(r'src=["\'](/_next/static/[^"\']+\.js)["\']', r.text)
for u in js_urls:
    t = requests.get('https://innovatecg.in' + u).text
    if 'baseURL' in t or 'NEXT_PUBLIC_' in t:
        b_matches = re.findall(r'(?:baseURL|API_URL|apiUrl|NEXT_PUBLIC_API[^=]*)\s*[:=]\s*["\']([^"\']+)["\']', t)
        if b_matches:
            print(f"Found base URLs in {u}:", set(b_matches))
