import requests

url = "https://cgbackend.nexallianceit.com/api/v1/voting/cast"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://innovatecg.in",
    "Referer": "https://innovatecg.in/",
    "Content-Type": "application/json"
}

payload = {
    "candidateId": "dummy",
    "voterName": "Test",
    "voterEmail": "test@test.com",
    "voterPhone": "9800000000",
    "tier": "Tier 3",
    "subCategory": "Education",
    "captchaId": "dummy",
    "captchaText": "12345"
}

try:
    r = requests.post(url, json=payload, headers=headers, timeout=10)
    print("Status Code:", r.status_code)
    print("Response Headers:", dict(r.headers))
    print("Response JSON:", r.text)
except Exception as e:
    print("Request Error:", e)
