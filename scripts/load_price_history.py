import os
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

database_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
engine = create_engine(database_url)

coin_id = "bitcoin"
days = 30

url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"

params = {
    "vs_currency": "usd",
    "days": days
}

response = requests.get(url, params=params, timeout=30)
print("Status code:", response.status_code)

data = response.json()

prices = data["prices"]

df = pd.DataFrame(prices, columns=["price_timestamp", "price"])
df["price_timestamp"] = pd.to_datetime(df["price_timestamp"], unit="ms")
df["coin_id"] = coin_id

df = df[["coin_id", "price_timestamp", "price"]]

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
