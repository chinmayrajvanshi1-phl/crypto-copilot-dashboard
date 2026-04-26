# Crypto Copilot Dashboard

An interactive crypto analytics dashboard built with Streamlit, PostgreSQL, Plotly, and OpenAI. The app allows users to explore live market data, review coin-level price history, compare multiple cryptocurrencies, and ask AI-powered questions grounded in dashboard context.

## Project Overview

Crypto Copilot Dashboard is designed as an end-to-end analytics project that combines data engineering, dashboard development, forecasting, and AI-assisted exploration in a single application.

The project pulls cryptocurrency data, stores it in PostgreSQL, visualizes key market trends in Streamlit, and provides contextual AI summaries and question answering across different dashboard views.

## Features

- Live market overview using the latest coin snapshot data
- Coin Detail page with historical price trends and simple forecast projection
- Comparison page for analyzing multiple coins across a selected date range
- Date range filter for selecting how far back to analyze data
- AI-powered summaries and Q&A grounded in visible dashboard data
- CSV export for selected comparison results
- Modular code structure with separate app and utility logic

## Tech Stack

- Python
- Streamlit
- PostgreSQL
- SQLAlchemy
- Pandas
- NumPy
- Plotly
- OpenAI API
- Python Dotenv

## Project Structure

```text
crypto-copilot-dashboard/
│
├── app/
│   ├── main.py
│   └── ai_utils.py
│
├── scripts/
│   ├── create_tables.py
│   ├── fetch_coingecko_test.py
│   ├── load_market_snapshot.py
│   ├── load_multi_coin_history.py
│   ├── load_price_history.py
│   ├── load_top30_coin_history.py
│   └── test_postgres_connection.py
│
├── assets/
│   └── screenshots/
│
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── .env
```

## How It Works

The application reads crypto market and price history data from PostgreSQL and uses Streamlit to present the data through interactive tabs and filters.

Each dashboard tab supports context-aware AI interaction. Instead of answering from general internet knowledge, the assistant uses the currently visible dashboard context to explain metrics, summarize trends, and respond to follow-up questions.

## Setup Instructions

### 1. Clone the repository

```bash
git clone <your-github-repo-url>
cd crypto-copilot-dashboard
```

### 2. Create and activate a virtual environment

On Mac/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create your environment file

Create a `.env` file in the project root and copy the structure from `.env.example`.

Example:

```env
OPENAI_API_KEY=your_openai_api_key_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crypto_copilot
DB_USER=your_postgres_username
DB_PASSWORD=your_postgres_password
```

### 5. Set up the database

Run the database setup and data loading scripts as needed:

```bash
python scripts/create_tables.py
python scripts/test_postgres_connection.py
python scripts/load_market_snapshot.py
python scripts/load_multi_coin_history.py
```

Depending on your workflow, you may also use:

```bash
python scripts/load_price_history.py
python scripts/load_top30_coin_history.py
```

### 6. Run the app

```bash
streamlit run app/main.py
```

## Dashboard Pages

### Overview
Displays the latest market snapshot, top coin, filtered market capitalization, total volume, and average 24-hour change.

### Coin Detail
Shows a selected coin’s current stats, historical price trend, and a simple short-horizon forecast.

### Comparison
Compares multiple selected coins using either raw prices or normalized performance over a chosen time range.

### AI Insights
Provides AI-powered explanations and answers based on the dashboard context and selected filters.

## Example Questions You Can Ask

- What is the filtered market cap?
- How much did Bitcoin change in the last 5 days?
- Which coin performed best in this selected range?
- What does the forecast suggest for Ethereum?
- If I invested $100 based on this forecast, what would that become?

## Screenshots

### Overview
![Overview Dashboard](assets/screenshots/1.png)

### Coin Detail
![Coin Detail Dashboard](assets/screenshots/2.png)

### Comparison
![Comparison Dashboard](assets/screenshots/3.png)

## Key Learning Outcomes

This project demonstrates:

- Building an end-to-end analytics workflow using Python and PostgreSQL
- Designing interactive dashboards in Streamlit
- Creating reusable app architecture with modular Python files
- Using Plotly for exploratory analysis and trend visualization
- Integrating AI into analytics workflows with grounded context
- Improving user experience through debugging, formatting fixes, and iterative enhancement

## Future Improvements

- Deploy the app to Streamlit Community Cloud
- Add stronger forecasting methods
- Add automated data refresh jobs
- Expand AI question handling for more coin-specific and comparative prompts
- Convert the tabbed layout into a full multipage Streamlit app

## Notes

This project is intended for educational, portfolio, and demonstration purposes.

The forecast functionality is a simple trend-based estimate and should not be treated as financial advice.

## Author

Chinmay Rajvanshi

MS in Business Intelligence & Analytics  
Data Analytics | BI | Product Analytics | AI-Enabled Dashboards