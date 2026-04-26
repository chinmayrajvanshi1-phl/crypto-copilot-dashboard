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

url = "https://api.coingecko.com/api/v3/coins/markets"

params = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 25,
    "page": 1,
    "sparkline": "false",
    "price_change_percentage": "24h"
}

response = requests.get(url, params=params, timeout=30)
print("Status code:", response.status_code)

data = response.json()
df = pd.DataFrame(data)

df = df[[
    "id",
    "symbol",
    "name",
    "current_price",
    "market_cap",
    "total_volume",
    "price_change_percentage_24h"
]].copy()

df = df.rename(columns={
    "id": "coin_id"
})

print("\nPreview of data to load:")
print(df.head())

df.to_sql(
    "coin_market_snapshot",
    con=engine,
    if_exists="append",
    index=False
)

print("\nMarket snapshot loaded successfully!")
print(f"Rows inserted: {len(df)}")