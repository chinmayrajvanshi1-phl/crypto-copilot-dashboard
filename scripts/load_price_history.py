import os
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL is missing from .env")

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_recycle=300
)

coin_id = "bitcoin"
days = 30

url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"

params = {
    "vs_currency": "usd",
    "days": days
}

response = requests.get(url, params=params, timeout=30)
print("Status code:", response.status_code)
response.raise_for_status()

data = response.json()
prices = data.get("prices", [])

if not prices:
    print("No price data returned.")
    raise SystemExit()

df = pd.DataFrame(prices, columns=["price_timestamp", "price"])
df["price_timestamp"] = pd.to_datetime(df["price_timestamp"], unit="ms", utc=True)
df["coin_id"] = coin_id
df = df[["coin_id", "price_timestamp", "price"]]
df = df.drop_duplicates(subset=["coin_id", "price_timestamp"]).copy()

print("\nPreview of history data to load:")
print(df.head())

df.to_sql(
    "coin_price_history",
    con=engine,
    if_exists="append",
    index=False
)

print("\nPrice history loaded successfully!")
print(f"Rows inserted: {len(df)}")