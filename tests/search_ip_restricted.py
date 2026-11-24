import requests
import re

r = requests.get('https://innovatecg.in/voting', headers={'User-Agent': 'Mozilla/5.0'})
js_urls = re.findall(r'src=["\'](/_next/static/[^"\']+\.js)["\']', r.text)

keywords = ['ip restricted', 'restricted', 'ip address', 'rate limit', 'too many', 'maximum votes from this ip', 'blocked']

for u in js_urls:
    full_u = 'https://innovatecg.in' + u
    try:
        js = requests.get(full_u).text
        for kw in keywords:
            if kw.lower() in js.lower():
                print(f"Match for '{kw}' in {u}:")
                matches = [m.start() for m in re.finditer(re.escape(kw), js, re.IGNORECASE)]
                for m in matches[:3]:
                    snippet = js[max(0, m-80):min(len(js), m+120)]
                    print(f"  Snippet: {snippet.strip()}\n")
    except Exception as e:
        pass
