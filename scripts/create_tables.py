import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise ValueError("DATABASE_URL is missing from .env")

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_recycle=300
)

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
    snapshot_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
"""

create_price_history_table = """
CREATE TABLE IF NOT EXISTS coin_price_history (
    id SERIAL PRIMARY KEY,
    coin_id TEXT NOT NULL,
    price_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    price NUMERIC,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_coin_price_history_coin_time UNIQUE (coin_id, price_timestamp)
);
"""

create_indexes = [
    """
    CREATE INDEX IF NOT EXISTS idx_coin_market_snapshot_coin_id
    ON coin_market_snapshot (coin_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_coin_market_snapshot_snapshot_time
    ON coin_market_snapshot (snapshot_time);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_coin_price_history_coin_id
    ON coin_price_history (coin_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_coin_price_history_price_timestamp
    ON coin_price_history (price_timestamp);
    """
]

with engine.connect() as connection:
    connection.execute(text(create_market_snapshot_table))
    connection.execute(text(create_price_history_table))

    for index_sql in create_indexes:
        connection.execute(text(index_sql))

    connection.commit()

print("Tables and indexes created successfully!")