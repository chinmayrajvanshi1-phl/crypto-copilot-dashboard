import os
import time

import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

database_url = os.getenv("DATABASE_URL")
coingecko_demo_api_key = os.getenv("COINGECKO_DEMO_API_KEY")

if not database_url:
    raise ValueError("DATABASE_URL is missing from .env")

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_recycle=300
)

headers = {}
if coingecko_demo_api_key:
    headers["x-cg-demo-api-key"] = coingecko_demo_api_key

markets_url = "https://api.coingecko.com/api/v3/coins/markets"
markets_params = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 30,
    "page": 1,
    "sparkline": "false"
}

markets_response = requests.get(
    markets_url,
    params=markets_params,
    headers=headers,
    timeout=30
)
print("Top 30 markets status code:", markets_response.status_code)
markets_response.raise_for_status()

markets_data = markets_response.json()
top_coin_ids = [coin["id"] for coin in markets_data]

print("\nTop 30 coin IDs:")
print(top_coin_ids)

days = 365
all_history = []

for i, coin_id in enumerate(top_coin_ids, start=1):
    print(f"\nFetching history for {i}/30: {coin_id}")

    history_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    history_params = {
        "vs_currency": "usd",
        "days": days,
        "interval": "daily"
    }

    history_response = requests.get(
        history_url,
        params=history_params,
        headers=headers,
        timeout=30
    )
    print("Status code:", history_response.status_code)

    if history_response.status_code == 200:
        history_data = history_response.json()
        prices = history_data.get("prices", [])

        if prices:
            df = pd.DataFrame(prices, columns=["price_timestamp", "price"])
            df["price_timestamp"] = pd.to_datetime(df["price_timestamp"], unit="ms", utc=True)
            df["coin_id"] = coin_id
            df = df[["coin_id", "price_timestamp", "price"]]
            all_history.append(df)
        else:
            print(f"No price history returned for {coin_id}")
    else:
        print(f"Failed for {coin_id}: {history_response.text}")

    time.sleep(2)

if all_history:
    final_df = pd.concat(all_history, ignore_index=True)
    final_df = final_df.drop_duplicates(subset=["coin_id", "price_timestamp"]).copy()

    print("\nPreview of combined history data:")
    print(final_df.head())

    final_df.to_sql(
        "coin_price_history",
        con=engine,
        if_exists="append",
        index=False
    )

    print("\nTop 30 coin price history loaded successfully!")
    print(f"Rows inserted: {len(final_df)}")
else:
    print("No history data was loaded.")