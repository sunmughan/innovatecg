import requests
import re

r = requests.get('https://innovatecg.in/voting', headers={'User-Agent': 'Mozilla/5.0'})
js_urls = re.findall(r'src=["\'](/_next/static/[^"\']+\.js)["\']', r.text)
print(f"Found {len(js_urls)} JS bundles")

keywords = ['already voted', 'duplicate', 'already cast', 'already registered', 'voted in this category', '1 vote per', 'already submitted', 'only 1 vote']

for u in js_urls:
    full_u = 'https://innovatecg.in' + u
    try:
        js_text = requests.get(full_u).text
        for kw in keywords:
            if kw.lower() in js_text.lower():
                print(f"Match for '{kw}' in {u}")
                idx = js_text.lower().find(kw.lower())
                snippet = js_text[max(0, idx-100):min(len(js_text), idx+150)]
                print(f"Snippet: {snippet}\n")
    except Exception as e:
        pass
