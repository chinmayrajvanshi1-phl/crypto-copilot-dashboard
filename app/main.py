import os
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine

from ai_utils import (
    normalize_text,
    format_money,
    format_money_int,
    format_pct,
    build_overview_summary,
    build_detail_summary,
    build_comparison_summary_text,
    build_ai_context,
    try_rule_based_answer,
    render_plain_text_box,
    render_chat_text,
)

load_dotenv()

st.set_page_config(
    page_title="AI Crypto Dashboard - By Chinmay Rajvanshi",
    layout="wide"
)


def get_engine():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is missing from .env or Streamlit secrets")
    return create_engine(database_url, pool_pre_ping=True, pool_recycle=300)


def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


engine = get_engine()
client = get_openai_client()

def render_header():
    linkedin_url = "https://www.linkedin.com/in/chinmayrajvanshi/"
    linkedin_logo = "https://cdn-icons-png.flaticon.com/512/174/174857.png"

    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:0.25rem;">
            <h1 style="margin:0; font-size:2.1rem;">AI Crypto Dashboard - By Chinmay Rajvanshi</h1>
            <a href="{linkedin_url}" target="_blank" style="display:flex; align-items:center;">
                <img src="{linkedin_logo}" width="28" style="display:block;" />
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )


@st.cache_data
def load_latest_market_data():
    query = """
        SELECT DISTINCT ON (coin_id)
            coin_id,
            symbol,
            name,
            current_price,
            market_cap,
            total_volume,
            price_change_percentage_24h,
            snapshot_time
        FROM coin_market_snapshot
        ORDER BY coin_id, snapshot_time DESC
    """
    df = pd.read_sql(query, engine)
    df["snapshot_time"] = pd.to_datetime(df["snapshot_time"], utc=True)
    return df


@st.cache_data
def load_history_data():
    query = """
        SELECT coin_id, price_timestamp, price
        FROM coin_price_history
        ORDER BY price_timestamp ASC
    """
    df = pd.read_sql(query, engine)
    df["price_timestamp"] = pd.to_datetime(df["price_timestamp"], utc=True)
    return df


@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def init_chat_state():
    keys = ["overview", "detail", "comparison", "ai_insights"]
    for key in keys:
        chat_key = f"{key}_chat_history"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []

    if "selected_page" not in st.session_state:
        st.session_state["selected_page"] = "Overview"


def render_page_navigation():
    selected = st.segmented_control(
        "Navigate pages",
        options=["Overview", "Coin Detail", "Comparison", "AI Insights"],
        default=st.session_state["selected_page"],
        key="page_nav_control"
    )

    if selected:
        st.session_state["selected_page"] = selected

    return st.session_state["selected_page"]


def resolve_date_range(preset_range, min_history_date, max_history_date, label):
    if preset_range == "7D":
        start_date = max(min_history_date, max_history_date - timedelta(days=7))
        end_date = max_history_date
    elif preset_range == "14D":
        start_date = max(min_history_date, max_history_date - timedelta(days=14))
        end_date = max_history_date
    elif preset_range == "30D":
        start_date = max(min_history_date, max_history_date - timedelta(days=30))
        end_date = max_history_date
    elif preset_range == "90D":
        start_date = max(min_history_date, max_history_date - timedelta(days=90))
        end_date = max_history_date
    elif preset_range == "180D":
        start_date = max(min_history_date, max_history_date - timedelta(days=180))
        end_date = max_history_date
    elif preset_range == "365D":
        start_date = max(min_history_date, max_history_date - timedelta(days=365))
        end_date = max_history_date
    elif preset_range == "Max":
        start_date = min_history_date
        end_date = max_history_date
    else:
        selected_date_range = st.sidebar.date_input(
            label,
            value=(min_history_date, max_history_date),
            min_value=min_history_date,
            max_value=max_history_date
        )

        if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2:
            start_date, end_date = selected_date_range
        else:
            start_date = min_history_date
            end_date = max_history_date

    return start_date, end_date


def get_sidebar_filters(market_df, history_df, selected_page):
    coin_options = sorted(market_df["coin_id"].unique().tolist())
    min_history_date = history_df["price_timestamp"].min().date()
    max_history_date = history_df["price_timestamp"].max().date()

    st.sidebar.header("Filters")
    st.sidebar.caption(f"Filters available for: {selected_page}")

    filters = {
        "selected_coin": coin_options[0] if coin_options else None,
        "top_n": 30,
        "sort_by": "market_cap",
        "comparison_coins": ["bitcoin", "ethereum", "solana"]
        if all(c in coin_options for c in ["bitcoin", "ethereum", "solana"])
        else coin_options[:3],
        "chart_mode": "Normalized Performance",
        "start_date": max(min_history_date, max_history_date - timedelta(days=30)),
        "end_date": max_history_date,
        "forecast_horizon": 3,
    }

    if selected_page == "Overview":
        filters["top_n"] = st.sidebar.selectbox(
            "Show top N coins",
            [5, 10, 15, 25, 30],
            index=4
        )

        filters["sort_by"] = st.sidebar.selectbox(
            "Sort market table by",
            ["market_cap", "current_price", "total_volume", "price_change_percentage_24h"]
        )

    elif selected_page == "Coin Detail":
        filters["selected_coin"] = st.sidebar.selectbox(
            "Choose a coin",
            coin_options
        )

        preset_range = st.sidebar.segmented_control(
            "Quick range",
            options=["7D", "14D", "30D", "90D", "180D", "365D", "Max", "Custom"],
            default="30D"
        )

        filters["start_date"], filters["end_date"] = resolve_date_range(
            preset_range,
            min_history_date,
            max_history_date,
            "Select history date range"
        )

        filters["forecast_horizon"] = st.sidebar.selectbox(
            "Forecast horizon",
            [1, 2, 3, 5, 7],
            index=2
        )

    elif selected_page == "Comparison":
        st.sidebar.subheader("Choose coins to compare")

        selected_compare = []
        default_compare = ["bitcoin", "ethereum", "solana"]
        default_compare = [c for c in default_compare if c in coin_options]

        for coin in coin_options:
            checked = st.sidebar.checkbox(
                coin,
                value=coin in default_compare,
                key=f"compare_{coin}"
            )
            if checked:
                selected_compare.append(coin)

        filters["comparison_coins"] = selected_compare

        filters["chart_mode"] = st.sidebar.radio(
            "Comparison chart mode",
            ["Raw Price", "Normalized Performance"],
            index=1
        )

        preset_range = st.sidebar.segmented_control(
            "Quick range",
            options=["7D", "14D", "30D", "90D", "180D", "365D", "Max", "Custom"],
            default="30D"
        )

        filters["start_date"], filters["end_date"] = resolve_date_range(
            preset_range,
            min_history_date,
            max_history_date,
            "Select comparison date range"
        )

    elif selected_page == "AI Insights":
        preset_range = st.sidebar.segmented_control(
            "Quick range",
            options=["7D", "14D", "30D", "90D", "180D", "365D", "Max", "Custom"],
            default="30D"
        )

        filters["start_date"], filters["end_date"] = resolve_date_range(
            preset_range,
            min_history_date,
            max_history_date,
            "Select AI insights date range"
        )

    return filters


def filter_history_data(history_df, start_date, end_date):
    return history_df[
        history_df["price_timestamp"].dt.date.between(start_date, end_date)
    ].copy()


def filter_market_data(market_df, sort_by, top_n):
    return market_df.sort_values(by=sort_by, ascending=False).head(top_n).copy()


def build_overview_metrics(market_df, filtered_market_df):
    latest_snapshot_time = market_df["snapshot_time"].max()
    top_coin = market_df.sort_values(by="market_cap", ascending=False).iloc[0]
    total_market_cap = filtered_market_df["market_cap"].sum()
    total_volume = filtered_market_df["total_volume"].sum()
    avg_change_24h = filtered_market_df["price_change_percentage_24h"].mean()

    return {
        "latest_snapshot_time": latest_snapshot_time,
        "top_coin": top_coin,
        "total_market_cap": total_market_cap,
        "total_volume": total_volume,
        "avg_change_24h": avg_change_24h,
    }


def build_comparison_summary(comparison_history):
    comparison_history = comparison_history.sort_values(["coin_id", "price_timestamp"]).copy()

    performance_summary = (
        comparison_history.groupby("coin_id")
        .agg(
            start_price=("price", "first"),
            end_price=("price", "last"),
            start_time=("price_timestamp", "first"),
            end_time=("price_timestamp", "last")
        )
        .reset_index()
    )

    performance_summary["return_pct"] = (
        (performance_summary["end_price"] - performance_summary["start_price"])
        / performance_summary["start_price"]
    ) * 100

    comparison_history["normalized_price"] = (
        comparison_history["price"]
        / comparison_history.groupby("coin_id")["price"].transform("first")
    ) * 100

    best_coin = performance_summary.sort_values("return_pct", ascending=False).iloc[0]
    worst_coin = performance_summary.sort_values("return_pct", ascending=True).iloc[0]
    avg_return = performance_summary["return_pct"].mean()

    return comparison_history, performance_summary, best_coin, worst_coin, avg_return


def generate_forecast(selected_coin_history, forecast_horizon):
    forecast_columns = [
        "forecast_timestamp",
        "forecast_price",
        "lower_bound",
        "upper_bound"
    ]

    if selected_coin_history.empty or len(selected_coin_history) < 7:
        return pd.DataFrame(columns=forecast_columns), None

    history = selected_coin_history.sort_values("price_timestamp").copy()
    history["return"] = history["price"].pct_change()
    returns = history["return"].dropna()

    if returns.empty:
        return pd.DataFrame(columns=forecast_columns), None

    avg_return = returns.tail(min(7, len(returns))).mean()
    volatility = returns.tail(min(14, len(returns))).std()

    if pd.isna(volatility):
        volatility = 0.0

    last_price = history["price"].iloc[-1]
    last_timestamp = history["price_timestamp"].iloc[-1]

    forecast_rows = []
    current_price = last_price

    for step in range(1, forecast_horizon + 1):
        current_price = current_price * (1 + avg_return)
        uncertainty = current_price * volatility * np.sqrt(step)

        forecast_rows.append({
            "forecast_timestamp": last_timestamp + pd.Timedelta(days=step),
            "forecast_price": current_price,
            "lower_bound": max(current_price - uncertainty, 0),
            "upper_bound": current_price + uncertainty
        })

    forecast_df = pd.DataFrame(forecast_rows)

    summary = {
        "last_price": last_price,
        "forecast_end_price": forecast_df["forecast_price"].iloc[-1],
        "forecast_change_pct": ((forecast_df["forecast_price"].iloc[-1] - last_price) / last_price) * 100,
        "volatility_pct": volatility * 100
    }

    return forecast_df, summary


def get_ai_response(system_context, user_prompt):
    if client is None:
        return "OPENAI_API_KEY is missing in your .env file."

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"{system_context}\n\nUser question: {user_prompt}"
    )
    return normalize_text(response.output_text)


def render_ai_section(title, summary_text, context_text, chat_key, input_key, data_bundle):
    st.subheader(title)
    render_plain_text_box(summary_text)

    for message in st.session_state[chat_key]:
        with st.chat_message(message["role"]):
            render_chat_text(message["content"])

    user_prompt = st.chat_input("Ask a question about this page", key=input_key)

    if user_prompt:
        user_prompt = normalize_text(user_prompt)
        st.session_state[chat_key].append({"role": "user", "content": user_prompt})

        with st.chat_message("user"):
            render_chat_text(user_prompt)

        rule_answer = try_rule_based_answer(user_prompt, data_bundle, chat_key)

        if rule_answer is not None:
            answer = rule_answer
        else:
            system_context = build_ai_context(
                page_name=title,
                page_summary=summary_text,
                extra_context=context_text,
                history_key=chat_key
            )
            answer = get_ai_response(system_context, user_prompt)

        answer = normalize_text(answer)

        with st.chat_message("assistant"):
            render_chat_text(answer)

        st.session_state[chat_key].append({"role": "assistant", "content": answer})


def render_overview_tab(filtered_market_df, metrics, history_df, start_date, end_date):
    summary_text = build_overview_summary(metrics, start_date, end_date)

    context_text = (
        f"Overview metrics: top coin is {metrics['top_coin']['name']}, "
        f"top coin price is {format_money(metrics['top_coin']['current_price'])}, "
        f"filtered market cap is {format_money_int(metrics['total_market_cap'])}, "
        f"total volume is {format_money_int(metrics['total_volume'])}, "
        f"and average 24-hour change is {format_pct(metrics['avg_change_24h'])}."
    )

    data_bundle = {
        "filtered_market_cap": metrics["total_market_cap"],
        "history_df": history_df
    }

    render_ai_section(
        title="AI Overview Summary",
        summary_text=summary_text,
        context_text=context_text,
        chat_key="overview_chat_history",
        input_key="overview_chat_input",
        data_bundle=data_bundle
    )

    st.subheader("Market Overview")
    st.caption(
        f"Latest snapshot: {metrics['latest_snapshot_time']} | History window: {start_date} to {end_date}"
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Top Coin", metrics["top_coin"]["name"])
    col2.metric("Top Coin Price", f"${metrics['top_coin']['current_price']:,.2f}")
    col3.metric("Filtered Market Cap", f"${metrics['total_market_cap']:,.0f}")
    col4.metric("Avg 24h Change", f"{metrics['avg_change_24h']:.2f}%")

    st.subheader("Market Snapshot")
    st.dataframe(
        filtered_market_df[[
            "coin_id", "symbol", "name", "current_price",
            "market_cap", "total_volume", "price_change_percentage_24h"
        ]],
        column_config={
            "coin_id": "Coin ID",
            "symbol": "Symbol",
            "name": "Name",
            "current_price": st.column_config.NumberColumn("Current Price", format="$%.2f"),
            "market_cap": st.column_config.NumberColumn("Market Cap", format="$%.0f"),
            "total_volume": st.column_config.NumberColumn("Total Volume", format="$%.0f"),
            "price_change_percentage_24h": st.column_config.NumberColumn("24h Change %", format="%.2f %%")
        },
        use_container_width=True
    )


def render_detail_tab(market_df, filtered_history_df, selected_coin, start_date, end_date, forecast_horizon):
    st.subheader(f"{selected_coin.title()} Detail View")

    selected_coin_market = market_df[market_df["coin_id"] == selected_coin]
    selected_coin_history = filtered_history_df[filtered_history_df["coin_id"] == selected_coin].copy()

    forecast_df = pd.DataFrame()
    forecast_summary = None

    if not selected_coin_market.empty:
        row = selected_coin_market.iloc[0]

        if not selected_coin_history.empty:
            forecast_df, forecast_summary = generate_forecast(selected_coin_history, forecast_horizon)

        detail_summary = build_detail_summary(
            selected_coin,
            row,
            start_date,
            end_date,
            forecast_summary
        )

        context_text = (
            f"Selected coin is {row['name']}. Current price is {format_money(row['current_price'])}. "
            f"Market cap is {format_money_int(row['market_cap'])}. Total volume is {format_money_int(row['total_volume'])}. "
            f"24-hour change is {format_pct(row['price_change_percentage_24h'])}. "
            f"Date window is {start_date} to {end_date}. "
        )

        if forecast_summary:
            context_text += (
                f"Forecast end price is {format_money(forecast_summary['forecast_end_price'])}. "
                f"Forecast change is {format_pct(forecast_summary['forecast_change_pct'])}. "
            )

        data_bundle = {
            "selected_coin": selected_coin,
            "forecast_summary": forecast_summary
        }

        render_ai_section(
            title="AI Coin Detail Summary",
            summary_text=detail_summary,
            context_text=context_text,
            chat_key="detail_chat_history",
            input_key="detail_chat_input",
            data_bundle=data_bundle
        )

        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Current Price", f"${row['current_price']:,.2f}")
        d2.metric("Market Cap", f"${row['market_cap']:,.0f}")
        d3.metric("Total Volume", f"${row['total_volume']:,.0f}")
        d4.metric("24h Change", f"{row['price_change_percentage_24h']:.2f}%")

    st.caption(f"Showing historical data from {start_date} to {end_date}")

    if not selected_coin_history.empty:
        fig_detail = go.Figure()

        fig_detail.add_trace(
            go.Scatter(
                x=selected_coin_history["price_timestamp"],
                y=selected_coin_history["price"],
                mode="lines",
                name="Historical Price"
            )
        )

        if not forecast_df.empty:
            fig_detail.add_trace(
                go.Scatter(
                    x=forecast_df["forecast_timestamp"],
                    y=forecast_df["forecast_price"],
                    mode="lines+markers",
                    name="Forecast",
                    line=dict(dash="dash")
                )
            )

            fig_detail.add_trace(
                go.Scatter(
                    x=pd.concat([forecast_df["forecast_timestamp"], forecast_df["forecast_timestamp"][::-1]]),
                    y=pd.concat([forecast_df["upper_bound"], forecast_df["lower_bound"][::-1]]),
                    fill="toself",
                    fillcolor="rgba(99, 110, 250, 0.15)",
                    line=dict(color="rgba(255,255,255,0)"),
                    hoverinfo="skip",
                    name="Forecast Range"
                )
            )

        fig_detail.update_layout(
            title=f"{selected_coin.title()} Price Trend + Forecast",
            xaxis_title="Date",
            yaxis_title="Price (USD)"
        )
        fig_detail.update_yaxes(tickprefix="$")
        st.plotly_chart(fig_detail, use_container_width=True)

        st.subheader("Forecast Outlook")

        if forecast_summary:
            f1, f2, f3 = st.columns(3)
            f1.metric("Forecast Horizon", f"{forecast_horizon} day(s)")
            f2.metric("Projected End Price", f"${forecast_summary['forecast_end_price']:,.2f}")
            f3.metric("Projected Change", f"{forecast_summary['forecast_change_pct']:.2f}%")

            st.write(
                f"Forecast Insight: Based on the recent trend in the selected date window, the simple forecast suggests "
                f"{selected_coin} could move from {format_money(forecast_summary['last_price'])} to "
                f"{format_money(forecast_summary['forecast_end_price'])} over the next {forecast_horizon} day(s), "
                f"a projected change of {format_pct(forecast_summary['forecast_change_pct'])}."
            )

            st.caption(
                "This is a simple trend-based forecast using recent returns and volatility. "
                "It is for portfolio/demo purposes and should not be treated as financial advice."
            )

            st.dataframe(
                forecast_df,
                column_config={
                    "forecast_timestamp": "Forecast Date",
                    "forecast_price": st.column_config.NumberColumn("Forecast Price", format="$%.2f"),
                    "lower_bound": st.column_config.NumberColumn("Lower Bound", format="$%.2f"),
                    "upper_bound": st.column_config.NumberColumn("Upper Bound", format="$%.2f")
                },
                use_container_width=True
            )
        else:
            st.info("Not enough history is available to generate a forecast. At least 7 data points are recommended.")
    else:
        st.info("No history found for this coin in the selected date range.")


def render_comparison_tab(market_df, filtered_history_df, comparison_coins, chart_mode, start_date, end_date):
    st.subheader("Multi-Coin Comparison")
    st.caption(f"Selected window: {start_date} to {end_date} | Mode: {chart_mode}")

    if not comparison_coins:
        st.info("Please select at least one coin to compare.")
        return

    comparison_history = filtered_history_df[
        filtered_history_df["coin_id"].isin(comparison_coins)
    ].copy()

    if comparison_history.empty:
        st.info("No comparison data found for the selected date range.")
        return

    comparison_history, performance_summary, best_coin, worst_coin, avg_return = build_comparison_summary(
        comparison_history
    )

    comparison_summary_text = build_comparison_summary_text(
        best_coin,
        worst_coin,
        avg_return,
        start_date,
        end_date,
        chart_mode
    )

    context_text = (
        f"Comparison mode is {chart_mode}. Best performer is {best_coin['coin_id']} at {format_pct(best_coin['return_pct'])}. "
        f"Worst performer is {worst_coin['coin_id']} at {format_pct(worst_coin['return_pct'])}. "
        f"Average return is {format_pct(avg_return)}."
    )

    data_bundle = {
        "best_coin": best_coin,
        "worst_coin": worst_coin,
        "comparison_summary_df": performance_summary
    }

    render_ai_section(
        title="AI Comparison Summary",
        summary_text=comparison_summary_text,
        context_text=context_text,
        chat_key="comparison_chat_history",
        input_key="comparison_chat_input",
        data_bundle=data_bundle
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Best Performer", best_coin["coin_id"], f"{best_coin['return_pct']:.2f}%")
    m2.metric("Worst Performer", worst_coin["coin_id"], f"{worst_coin['return_pct']:.2f}%")
    m3.metric("Average Return", f"{avg_return:.2f}%")

    st.write(
        f"Range Insight: Over the selected period, {best_coin['coin_id']} was the strongest performer at "
        f"{format_pct(best_coin['return_pct'])}, while {worst_coin['coin_id']} was the weakest at "
        f"{format_pct(worst_coin['return_pct'])}. The average return across the selected coins was {format_pct(avg_return)}."
    )

    if chart_mode == "Raw Price":
        fig_compare = px.line(
            comparison_history,
            x="price_timestamp",
            y="price",
            color="coin_id",
            title="Raw Price Comparison"
        )
        fig_compare.update_layout(xaxis_title="Date", yaxis_title="Price (USD)")
        fig_compare.update_yaxes(tickprefix="$")
    else:
        fig_compare = px.line(
            comparison_history,
            x="price_timestamp",
            y="normalized_price",
            color="coin_id",
            title="Normalized Performance (Start = 100)"
        )
        fig_compare.update_layout(xaxis_title="Date", yaxis_title="Normalized Index")

    st.plotly_chart(fig_compare, use_container_width=True)

    performance_summary = performance_summary.sort_values("return_pct", ascending=False)

    st.subheader("Selected Range Performance")
    st.dataframe(
        performance_summary[[
            "coin_id", "start_time", "end_time",
            "start_price", "end_price", "return_pct"
        ]],
        column_config={
            "coin_id": "Coin ID",
            "start_time": "Start Time",
            "end_time": "End Time",
            "start_price": st.column_config.NumberColumn("Start Price", format="$%.2f"),
            "end_price": st.column_config.NumberColumn("End Price", format="$%.2f"),
            "return_pct": st.column_config.NumberColumn("Return %", format="%.2f %%")
        },
        use_container_width=True
    )

    csv_data = convert_df_to_csv(performance_summary)
    st.download_button(
        label="Download performance CSV",
        data=csv_data,
        file_name="coin_performance_summary.csv",
        mime="text/csv"
    )

    latest_compare = market_df[market_df["coin_id"].isin(comparison_coins)].copy()
    st.subheader("Comparison Snapshot")
    st.dataframe(
        latest_compare[[
            "coin_id", "name", "current_price",
            "market_cap", "total_volume", "price_change_percentage_24h"
        ]],
        column_config={
            "coin_id": "Coin ID",
            "name": "Name",
            "current_price": st.column_config.NumberColumn("Current Price", format="$%.2f"),
            "market_cap": st.column_config.NumberColumn("Market Cap", format="$%.0f"),
            "total_volume": st.column_config.NumberColumn("Total Volume", format="$%.0f"),
            "price_change_percentage_24h": st.column_config.NumberColumn("24h Change %", format="%.2f %%")
        },
        use_container_width=True
    )


def render_ai_insights_tab(metrics, filtered_market_df, start_date, end_date):
    summary_text = (
        f"This page provides broader AI insights for the current dashboard window from {start_date} to {end_date}. "
        f"{metrics['top_coin']['name']} is currently the leading coin by market cap."
    )

    context_text = (
        f"Top coin is {metrics['top_coin']['name']}. "
        f"Top coin price is {format_money(metrics['top_coin']['current_price'])}. "
        f"Filtered market cap is {format_money_int(metrics['total_market_cap'])}. "
        f"Total volume is {format_money_int(metrics['total_volume'])}. "
        f"Average 24-hour change is {format_pct(metrics['avg_change_24h'])}."
    )

    data_bundle = {
        "filtered_market_cap": metrics["total_market_cap"]
    }

    render_ai_section(
        title="AI Insights",
        summary_text=summary_text,
        context_text=context_text,
        chat_key="ai_insights_chat_history",
        input_key="ai_insights_chat_input",
        data_bundle=data_bundle
    )


def main():
    init_chat_state()

    market_df = load_latest_market_data()
    history_df = load_history_data()

    render_header()
    st.caption(
        "AI-powered interactive crypto analytics dashboard with built-in insights and a conversational assistant "
        "that answers user queries, leveraging CoinGecko, PostgreSQL, Streamlit, Plotly, and forecasting capabilities."
    )

    if market_df.empty:
        st.warning("No market data found in the database.")
        st.stop()

    if history_df.empty:
        st.warning("No history data found in the database.")
        st.stop()

    selected_page = render_page_navigation()

    filters = get_sidebar_filters(market_df, history_df, selected_page)

    filtered_history_df = filter_history_data(
        history_df,
        filters["start_date"],
        filters["end_date"]
    )

    filtered_market_df = filter_market_data(
        market_df,
        filters["sort_by"],
        filters["top_n"]
    )

    metrics = build_overview_metrics(market_df, filtered_market_df)

    if selected_page == "Overview":
        render_overview_tab(
            filtered_market_df,
            metrics,
            filtered_history_df,
            filters["start_date"],
            filters["end_date"]
        )

    elif selected_page == "Coin Detail":
        render_detail_tab(
            market_df,
            filtered_history_df,
            filters["selected_coin"],
            filters["start_date"],
            filters["end_date"],
            filters["forecast_horizon"]
        )

    elif selected_page == "Comparison":
        render_comparison_tab(
            market_df,
            filtered_history_df,
            filters["comparison_coins"],
            filters["chart_mode"],
            filters["start_date"],
            filters["end_date"]
        )

    elif selected_page == "AI Insights":
        render_ai_insights_tab(
            metrics,
            filtered_market_df,
            filters["start_date"],
            filters["end_date"]
        )


if __name__ == "__main__":
    main()