import requests
import json

url = "https://danjuanfunds.com/djapi/index_valuation/results?category=1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://danjuanfunds.com/rn/value-center"
}

response = requests.get(url, headers=headers)
data = response.json()
items = data.get('data', {}).get('items', [])
print(f"Items: {len(items)}")
for i in items:
    print(i.get('name'))
