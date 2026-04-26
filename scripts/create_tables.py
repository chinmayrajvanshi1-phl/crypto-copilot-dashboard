import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

database_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

engine = create_engine(database_url)

create_market_snapshot_table = """
CREATE TABLE IF NOT EXISTS coin_market_snapshot (
    id SERIAL PRIMARY KEY,
    coin_id TEXT NOT NULL,
    symbol TEXT,
    name TEXT,
    current_price NUMERIC,
    market_cap NUMERIC,
    total_volume NUMERIC,
    price_change_percentage_24h NUMERIC,
    snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

create_price_history_table = """
CREATE TABLE IF NOT EXISTS coin_price_history (
    id SERIAL PRIMARY KEY,
    coin_id TEXT NOT NULL,
    price_timestamp TIMESTAMP NOT NULL,
    price NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

with engine.connect() as connection:
    connection.execute(text(create_market_snapshot_table))
    connection.execute(text(create_price_history_table))
    connection.commit()

print("Tables created successfully!")