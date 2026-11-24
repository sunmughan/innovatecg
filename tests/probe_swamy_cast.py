import requests

url = "https://cgbackend.nexallianceit.com/api/v1/voting/cast"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://innovatecg.in",
    "Referer": "https://innovatecg.in/",
    "Content-Type": "application/json"
}

# Fetch candidateId of Sunmughan Swamy from tiers
r_tiers = requests.get("https://cgbackend.nexallianceit.com/api/v1/voting/tiers-with-candidates")
tiers_data = r_tiers.json().get("data", [])
swamy_id = None
for t in tiers_data:
    for c in t.get("candidates", []):
        if "swamy" in c.get("name", "").lower():
            swamy_id = c.get("_id")
            print("Found Swamy ID:", swamy_id, "Candidate name:", c.get("name"))
            break

# Now probe cast with real swamy_id and valid format email
payload = {
    "candidateId": swamy_id or "6724...",
    "voterName": "Sathish Shivaprasad",
    "voterEmail": "vikas.gupta@yahoo.com",
    "voterPhone": "9383465787",
    "tier": "Tier 3",
    "subCategory": "Digital Literacy and Skill Development Education",
    "captchaId": "12345",
    "captchaText": "dummy"
}

r = requests.post(url, json=payload, headers=headers, timeout=10)
print("Status Code:", r.status_code)
print("Response JSON:", r.text)
