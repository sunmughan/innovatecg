import requests
import re

r = requests.get('https://innovatecg.in/voting', headers={'User-Agent': 'Mozilla/5.0'})
js_urls = re.findall(r'src=["\'](/_next/static/[^"\']+\.js)["\']', r.text)
print(f"Found {len(js_urls)} JS files on live page:")

for u in js_urls:
    full_u = 'https://innovatecg.in' + u
    try:
        t = requests.get(full_u).text
        if 'castVote' in t or 'voting' in t.lower():
            if 'castVote' in t:
                print(f"*** Found 'castVote' in {u} ***")
                idx = t.find('castVote')
                print(t[max(0, idx-200):min(len(t), idx+400)])
                print('='*60)
    except Exception as e:
        pass
