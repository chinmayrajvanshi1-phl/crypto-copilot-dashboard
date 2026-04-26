import requests
import pandas as pd

url = "https://api.coingecko.com/api/v3/coins/markets"

params = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 10,
    "page": 1,
    "sparkline": "false",
    "price_change_percentage": "24h,7d"
}

response = requests.get(url, params=params)

print("Status code:", response.status_code)

data = response.json()

df = pd.DataFrame(data)

print(df[[
    "id",
    "symbol",
    "name",
    "current_price",
    "market_cap",
    "total_volume",
    "price_change_percentage_24h"
]].head())