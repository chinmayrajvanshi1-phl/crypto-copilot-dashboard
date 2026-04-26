import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL is missing from .env")

print("Connecting to DATABASE_URL")

try:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300
    )

    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        row = result.fetchone()
        print("Connected successfully!")
        print("PostgreSQL version:", row[0])

except Exception as e:
    print("Connection failed.")
    print("Error:", e)