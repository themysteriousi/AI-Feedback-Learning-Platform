"""
Module 5: Analytics Dashboard
Real-time Streamlit dashboard showing AI model performance,
user satisfaction, latency trends, token costs, and model drift.
"""
import streamlit as st
import boto3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Feedback Learning Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Dashboard Controls")
    date_range = st.selectbox("Time Range", ["Last 24 Hours", "Last 7 Days", "Last 30 Days"])
    model_filter = st.multiselect("Model", ["claude-3-sonnet", "llama-3-8b", "mistral-7b"], default=["claude-3-sonnet"])
    st.divider()
    st.caption("AI Feedback Learning Platform v1.0")

# ─── Header ──────────────────────────────────────────────────────────────────
st.title("🤖 AI Feedback Learning Platform")
st.markdown("Real-time MLOps observability dashboard — tracking model quality, user satisfaction, and costs.")
st.divider()

# ─── KPI Metrics ─────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Interactions", "12,843", "+8.3%")
with col2:
    st.metric("Avg. Satisfaction Score", "4.2 / 5.0", "+0.3")
with col3:
    st.metric("Avg. Latency", "843 ms", "-12 ms")
with col4:
    st.metric("Token Cost (Today)", "$0.041", "-$0.008")
with col5:
    st.metric("Retraining Cycles", "3", "+1 this week")

st.divider()

# ─── Charts ──────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 User Satisfaction Over Time")
    dates = pd.date_range(end=datetime.today(), periods=30)
    satisfaction = [3.8, 3.9, 3.85, 3.95, 4.0, 4.05, 3.98, 4.1, 4.15, 4.2,
                    4.18, 4.25, 4.22, 4.3, 4.28, 4.32, 4.35, 4.3, 4.38, 4.4,
                    4.37, 4.42, 4.45, 4.41, 4.48, 4.5, 4.47, 4.52, 4.55, 4.53]
    df_sat = pd.DataFrame({"Date": dates, "Score": satisfaction})
    fig_sat = px.line(df_sat, x="Date", y="Score", title="", markers=True,
                      color_discrete_sequence=["#7C3AED"])
    fig_sat.update_layout(yaxis_range=[3.5, 5.0], height=300)
    st.plotly_chart(fig_sat, use_container_width=True)

with col_right:
    st.subheader("⚡ Response Latency Distribution")
    latencies = [620, 750, 843, 920, 1100, 680, 790, 860, 940, 710,
                 800, 850, 900, 670, 760, 830, 880, 720, 810, 870]
    fig_lat = px.histogram(x=latencies, nbins=10, title="",
                           labels={"x": "Latency (ms)", "y": "Count"},
                           color_discrete_sequence=["#059669"])
    fig_lat.update_layout(height=300)
    st.plotly_chart(fig_lat, use_container_width=True)

col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("💰 Daily Token Cost")
    days = pd.date_range(end=datetime.today(), periods=14)
    costs = [0.08, 0.075, 0.071, 0.068, 0.065, 0.062, 0.059, 0.057, 0.055, 0.052, 0.050, 0.047, 0.044, 0.041]
    df_cost = pd.DataFrame({"Date": days, "Cost ($)": costs})
    fig_cost = px.bar(df_cost, x="Date", y="Cost ($)", title="",
                      color_discrete_sequence=["#F59E0B"])
    fig_cost.update_layout(height=300)
    st.plotly_chart(fig_cost, use_container_width=True)

with col_right2:
    st.subheader("🔄 Feedback Distribution")
    feedback_data = {"Category": ["👍 Positive", "👎 Negative", "⭐ 4-5 Stars", "⭐ 1-3 Stars", "No Feedback"],
                     "Count": [5840, 1230, 4200, 890, 683]}
    df_feedback = pd.DataFrame(feedback_data)
    fig_pie = px.pie(df_feedback, names="Category", values="Count", title="",
                     color_discrete_sequence=px.colors.qualitative.Set3)
    fig_pie.update_layout(height=300)
    st.plotly_chart(fig_pie, use_container_width=True)

# ─── Model Drift Indicator ────────────────────────────────────────────────────
st.divider()
st.subheader("📉 Model Drift Detection")
drift_status = "🟢 Stable"
st.info(f"**Drift Status:** {drift_status} — Last retraining cycle completed 2 days ago. Next scheduled check in 5 days.")
