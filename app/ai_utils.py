import html
import re

import pandas as pd
import streamlit as st


def normalize_text(text):
    if text is None:
        return ""

    text = str(text)
    text = text.replace("\u00a0", " ")
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def format_money(value):
    if pd.isna(value):
        return "N/A"
    return f"${value:,.2f}"


def format_money_int(value):
    if pd.isna(value):
        return "N/A"
    return f"${value:,.0f}"


def format_pct(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"


def extract_amount_from_prompt(prompt):
    matches = re.findall(r"\$?\s?(\d+(?:\.\d+)?)", prompt.lower())
    if matches:
        try:
            return float(matches[0])
        except ValueError:
            return None
    return None


def get_last_user_messages(chat_key, limit=4):
    history = st.session_state.get(chat_key, [])
    return [m["content"] for m in history if m["role"] == "user"][-limit:]


def calculate_coin_change_over_days(history_df, coin_id, days=5):
    coin_history = history_df[history_df["coin_id"] == coin_id].sort_values("price_timestamp").copy()

    if coin_history.empty or len(coin_history) < 2:
        return None

    latest_time = coin_history["price_timestamp"].max()
    target_time = latest_time - pd.Timedelta(days=days)

    earlier_rows = coin_history[coin_history["price_timestamp"] <= target_time]
    if earlier_rows.empty:
        return None

    latest_price = coin_history.iloc[-1]["price"]
    earlier_price = earlier_rows.iloc[-1]["price"]

    if earlier_price == 0:
        return None

    return ((latest_price - earlier_price) / earlier_price) * 100


def build_overview_summary(metrics, start_date, end_date):
    return (
        f"This page shows the current market overview from {start_date} to {end_date}. "
        f"The top coin by market cap is {metrics['top_coin']['name']} at {format_money(metrics['top_coin']['current_price'])}. "
        f"The filtered market cap is {format_money_int(metrics['total_market_cap'])}, "
        f"total volume is {format_money_int(metrics['total_volume'])}, "
        f"and the average 24-hour change is {format_pct(metrics['avg_change_24h'])}."
    )


def build_detail_summary(selected_coin, row, start_date, end_date, forecast_summary):
    base = (
        f"This page shows the detailed view for {selected_coin}. "
        f"Current price is {format_money(row['current_price'])}, market cap is {format_money_int(row['market_cap'])}, "
        f"total volume is {format_money_int(row['total_volume'])}, and 24-hour change is {format_pct(row['price_change_percentage_24h'])}. "
        f"The visible history window is {start_date} to {end_date}."
    )

    if forecast_summary:
        base += (
            f" The current forecast projects an end price of {format_money(forecast_summary['forecast_end_price'])}, "
            f"which implies a projected move of {format_pct(forecast_summary['forecast_change_pct'])}."
        )

    return base


def build_comparison_summary_text(best_coin, worst_coin, avg_return, start_date, end_date, chart_mode):
    return (
        f"This page compares the selected coins from {start_date} to {end_date} using {chart_mode.lower()} mode. "
        f"The best performer is {best_coin['coin_id']} at {format_pct(best_coin['return_pct'])}, "
        f"the worst performer is {worst_coin['coin_id']} at {format_pct(worst_coin['return_pct'])}, "
        f"and the average return is {format_pct(avg_return)}."
    )


def build_ai_context(page_name, page_summary, extra_context, history_key):
    history = st.session_state.get(history_key, [])
    history_text = (
        "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-6:]])
        if history
        else "No prior conversation."
    )

    return f"""
You are Crypto Copilot, a conversational AI assistant inside a crypto analytics dashboard.

Rules:
- Use only the dashboard context and recent conversation.
- Be concise and plain-English.
- Never say data is unavailable if the context already supports an answer.
- Do not restate raw database-style text.
- Use only normal spacing and simple sentences.
- If a user asks an analytics question and the answer is already computed, answer directly.

Current page: {page_name}

Page summary:
{page_summary}

Context:
{extra_context}

Recent conversation:
{history_text}
"""


def try_rule_based_answer(user_prompt, data_bundle, chat_key):
    prompt = user_prompt.lower().strip()
    recent_user_msgs = " ".join(get_last_user_messages(chat_key)).lower()

    if "filtered market cap" in prompt:
        return (
            f"Filtered market cap is the total market capitalization of the coins currently shown after your filters are applied. "
            f"In this view, that total is {format_money_int(data_bundle.get('filtered_market_cap', 0))}."
        )

    if "is this value for bitcoin" in prompt or "is this for bitcoin" in prompt:
        return "No. Filtered market cap is for the full filtered set of displayed coins, not just Bitcoin."

    if ("5 day" in prompt or "last 5 days" in prompt) and "bitcoin" in prompt and data_bundle.get("history_df") is not None:
        change = calculate_coin_change_over_days(data_bundle["history_df"], "bitcoin", 5)
        if change is not None:
            return f"Bitcoin changed by {format_pct(change)} over the last 5 days based on the available history."
        return "I do not have enough earlier Bitcoin history in the selected window to calculate a 5-day change."

    if ("best coin" in prompt or "best performer" in prompt or "performed best" in prompt) and data_bundle.get("best_coin") is not None:
        best_coin = data_bundle["best_coin"]
        return f"The best performer in the selected comparison window is {best_coin['coin_id']} with a return of {format_pct(best_coin['return_pct'])}."

    if ("worst coin" in prompt or "worst performer" in prompt or "performed worst" in prompt) and data_bundle.get("worst_coin") is not None:
        worst_coin = data_bundle["worst_coin"]
        return f"The worst performer in the selected comparison window is {worst_coin['coin_id']} with a return of {format_pct(worst_coin['return_pct'])}."

    if ("forecast" in prompt or "tomorrow" in prompt or "next day" in prompt) and data_bundle.get("forecast_summary") is not None:
        forecast_summary = data_bundle["forecast_summary"]
        selected_coin = data_bundle.get("selected_coin", "the selected coin")
        return (
            f"For {selected_coin}, the current simple forecast projects an end price of {format_money(forecast_summary['forecast_end_price'])}. "
            f"That implies a projected move of {format_pct(forecast_summary['forecast_change_pct'])} from the latest visible price."
        )

    amount = extract_amount_from_prompt(prompt)
    if amount is not None and data_bundle.get("forecast_summary") is not None:
        forecast_summary = data_bundle["forecast_summary"]
        growth = forecast_summary["forecast_change_pct"] / 100
        final_value = amount * (1 + growth)
        profit = final_value - amount
        selected_coin = data_bundle.get("selected_coin", "the selected coin")
        return (
            f"Using the current simple forecast for {selected_coin}, an investment of {format_money(amount)} could become about {format_money(final_value)}. "
            f"That would be an estimated gain of {format_money(profit)}. This is only a rough forecast, not financial advice."
        )

    if (
        ("same for" in prompt or "what about" in prompt or "and bitcoin" in prompt or "and ethereum" in prompt)
        and ("forecast" in recent_user_msgs or "invest" in recent_user_msgs or "tomorrow" in recent_user_msgs)
    ):
        return None

    return None


def render_plain_text_box(text, background="#eef4ff", border="#d9e6ff", color="#1f4e79"):
    escaped = html.escape(normalize_text(text))
    escaped = escaped.replace("\n", "<br>")
    st.markdown(
        f"""
        <div style="
            background:{background};
            border:1px solid {border};
            color:{color};
            padding:16px 18px;
            border-radius:10px;
            font-size:18px;
            line-height:1.6;
            white-space:normal;
            font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        ">
            {escaped}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chat_text(text):
    escaped = html.escape(normalize_text(text))
    escaped = escaped.replace("\n", "<br>")
    st.markdown(
        f"""
        <div style="
            white-space:normal;
            line-height:1.7;
            font-size:1rem;
            font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        ">
            {escaped}
        </div>
        """,
        unsafe_allow_html=True,
    )