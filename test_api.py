import requests
import json

url = "http://127.0.0.1:8007/positions"
data = {
    "ticker": "T",
    "shares": 150,
    "price_bought": 0,
    "date_bought": ""
}

try:
    response = requests.post(url, json=data)
    print("Status Code:", response.status_code)
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)
