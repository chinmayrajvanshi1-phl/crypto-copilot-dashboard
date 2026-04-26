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

print("Connecting to:", database_url.replace(db_password if db_password else "", "****"))

try:
    engine = create_engine(database_url)

    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        row = result.fetchone()
        print("Connected successfully!")
        print("PostgreSQL version:", row[0])

except Exception as e:
    print("Connection failed.")
    print("Error:", e)