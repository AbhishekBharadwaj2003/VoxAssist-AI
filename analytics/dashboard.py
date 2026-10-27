import pandas as pd
import streamlit as st
import plotly.express as px

from analytics.logger import ANALYTICS_FILE


# --------------------------------------------------
# Page configuration
# --------------------------------------------------
st.set_page_config(
    page_title="VoxAssist Analytics",
    page_icon="📊",
    layout="wide",
)


# --------------------------------------------------
# Header
# --------------------------------------------------
st.title("📊 VoxAssist Analytics Dashboard")
st.caption("Customer support performance and interaction insights")


# --------------------------------------------------
# Load analytics data
# --------------------------------------------------
@st.cache_data
def load_data(file_path, modified_time):
    if not file_path.exists() or file_path.stat().st_size == 0:
        return pd.DataFrame()

    df = pd.read_csv(file_path)

    required_columns = [
        "timestamp",
        "question",
        "channel",
        "response_time_seconds",
        "topic",
        "escalated",
    ]

    missing = [column for column in required_columns if column not in df.columns]

    if missing:
        raise ValueError(
            f"Analytics CSV is missing columns: {', '.join(missing)}"
        )

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["response_time_seconds"] = pd.to_numeric(
        df["response_time_seconds"], errors="coerce"
    )

    df["channel"] = df["channel"].astype(str).str.lower().str.strip()
    df["topic"] = df["topic"].fillna("General")

    df["escalated"] = (
        df["escalated"]
        .astype(str)
        .str.lower()
        .isin(["true", "1", "yes"])
    )

    return df


# --------------------------------------------------
# Refresh controls
# --------------------------------------------------
with st.sidebar:
    st.header("Dashboard Controls")

    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()

    st.caption("Data source: data/analytics.csv")


# --------------------------------------------------
# Read data
# --------------------------------------------------
try:
    modified_time = (
        ANALYTICS_FILE.stat().st_mtime
        if ANALYTICS_FILE.exists()
        else 0
    )

    df = load_data(ANALYTICS_FILE, modified_time)

except Exception as error:
    st.error(f"Could not load analytics data: {error}")
    st.stop()


if df.empty:
    st.info(
        "No analytics data found yet. Start the VoxAssist application, "
        "ask a few questions, and return here to refresh the dashboard."
    )
    st.stop()


# --------------------------------------------------
# Date filters
# --------------------------------------------------
valid_timestamps = df["timestamp"].dropna()

if not valid_timestamps.empty:
    min_date = valid_timestamps.min().date()
    max_date = valid_timestamps.max().date()

    with st.sidebar:
        selected_dates = st.date_input(
            "Filter by date",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start_date, end_date = selected_dates

        df = df[
            df["timestamp"].dt.date.between(start_date, end_date)
        ]
else:
    st.warning("No valid timestamps are available for date filtering.")


# --------------------------------------------------
# KPI metrics
# --------------------------------------------------
total_queries = len(df)

text_queries = int((df["channel"] == "text").sum())
voice_queries = int((df["channel"] == "voice").sum())

valid_response_times = df["response_time_seconds"].dropna()

average_response_time = (
    valid_response_times.mean()
    if not valid_response_times.empty
    else 0.0
)

escalated_queries = int(df["escalated"].sum())

escalation_rate = (
    escalated_queries / total_queries * 100
    if total_queries
    else 0.0
)


st.subheader("Key Performance Indicators")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Queries", total_queries)
col2.metric("Text Queries", text_queries)
col3.metric("Voice Queries", voice_queries)
col4.metric("Avg. Response Time", f"{average_response_time:.2f} sec")
col5.metric("Escalation Flag Rate", f"{escalation_rate:.1f}%")


st.divider()


# --------------------------------------------------
# Charts
# --------------------------------------------------
left, right = st.columns(2)


with left:
    st.subheader("Queries by Channel")

    channel_counts = (
        df["channel"]
        .value_counts()
        .rename_axis("Channel")
        .reset_index(name="Queries")
    )

    if not channel_counts.empty:
        fig_channel = px.pie(
            channel_counts,
            names="Channel",
            values="Queries",
            hole=0.45,
            title="Text vs Voice",
        )

        st.plotly_chart(fig_channel, use_container_width=True)
    else:
        st.info("No channel data available.")


with right:
    st.subheader("Most Common Topics")

    topic_counts = (
        df["topic"]
        .value_counts()
        .rename_axis("Topic")
        .reset_index(name="Queries")
    )

    if not topic_counts.empty:
        fig_topics = px.bar(
            topic_counts,
            x="Topic",
            y="Queries",
            title="Queries by Topic",
        )

        st.plotly_chart(fig_topics, use_container_width=True)
    else:
        st.info("No topic data available.")


# --------------------------------------------------
# Query trends
# --------------------------------------------------
st.subheader("Interaction Trends")

trend_data = df.dropna(subset=["timestamp"]).copy()

if not trend_data.empty:
    trend_data["Date"] = trend_data["timestamp"].dt.date

    daily_queries = (
        trend_data.groupby(["Date", "channel"])
        .size()
        .reset_index(name="Queries")
    )

    fig_trend = px.line(
        daily_queries,
        x="Date",
        y="Queries",
        color="channel",
        markers=True,
        title="Daily Queries by Channel",
    )

    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("No valid timestamps available for trend analysis.")


# --------------------------------------------------
# Recent interactions
# --------------------------------------------------
st.subheader("Recent Customer Interactions")

display_df = df.sort_values(
    "timestamp",
    ascending=False,
    na_position="last",
).copy()

display_df["escalated"] = display_df["escalated"].map(
    {True: "Flagged", False: "Not flagged"}
)

st.dataframe(
    display_df[
        [
            "timestamp",
            "question",
            "channel",
            "response_time_seconds",
            "topic",
            "escalated",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "Escalation flags are keyword-based estimates, not confirmed human "
    "handoffs. Response times measure AI response generation, excluding "
    "speech synthesis."
)