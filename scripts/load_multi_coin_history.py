import os
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL is missing from .env")

engine = create_engine(database_url)

coin_ids = ["bitcoin", "ethereum", "solana", "binancecoin", "ripple"]
days = 30

all_history = []

for coin_id in coin_ids:
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": days
    }

    response = requests.get(url, params=params, timeout=30)
    print(f"{coin_id} status code:", response.status_code)

    if response.status_code == 200:
        data = response.json()
        prices = data["prices"]

        df = pd.DataFrame(prices, columns=["price_timestamp", "price"])
        df["price_timestamp"] = pd.to_datetime(df["price_timestamp"], unit="ms")
        df["coin_id"] = coin_id
        df = df[["coin_id", "price_timestamp", "price"]]

        all_history.append(df)
    else:
        print(f"Failed for {coin_id}: {response.text}")

if all_history:
    final_df = pd.concat(all_history, ignore_index=True)

    print("\nPreview of combined history data:")
    print(final_df.head())

    final_df.to_sql(
        "coin_price_history",
        con=engine,
        if_exists="append",
        index=False
    )

    print("\nMulti-coin price history loaded successfully!")
    print(f"Rows inserted: {len(final_df)}")
else:
    print("No data loaded.")