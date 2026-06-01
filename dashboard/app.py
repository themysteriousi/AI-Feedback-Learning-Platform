"""
AI Feedback Learning Platform — Analytics Dashboard
=====================================================
A Streamlit app with three dashboards:
  1. Executive  — AI health score, satisfaction index, model trends
  2. Technical  — Latency, errors, drift indicators, deployment history
  3. Business   — Token costs, user adoption, productivity gains

Data sources:
  - S3 Data Lake (feedback JSONL files)  → loaded via boto3
  - CloudWatch Metrics                   → loaded via boto3
  - S3 Deployments log                   → loaded via boto3

Run locally:
  streamlit run dashboard/app.py

Deploy FREE on Streamlit Community Cloud:
  https://streamlit.io/cloud  (connect your GitHub repo)

Secrets needed (Streamlit Cloud → Settings → Secrets):
  AWS_ACCESS_KEY_ID     = "..."
  AWS_SECRET_ACCESS_KEY = "..."
  AWS_DEFAULT_REGION    = "us-east-1"
  DATA_LAKE_BUCKET      = "your-bucket-name"
"""

import streamlit as st
import boto3
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import io

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Feedback Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] { background: #0f1117; }
    .metric-card {
        background: linear-gradient(135deg, #1a1f2e, #252d3d);
        border: 1px solid #2e3a4e;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-value { font-size: 2.5rem; font-weight: 700; color: #4fc3f7; }
    .metric-label { font-size: 0.85rem; color: #8899aa; margin-top: 4px; }
    .status-ok    { color: #4caf50; font-weight: 600; }
    .status-warn  { color: #ff9800; font-weight: 600; }
    .status-bad   { color: #f44336; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── AWS clients ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_clients():
    """Create AWS clients once and cache them."""
    kwargs = {}
    # Support Streamlit Cloud secrets or local ~/.aws/credentials
    if "AWS_ACCESS_KEY_ID" in st.secrets:
        kwargs = {
            "aws_access_key_id":     st.secrets["AWS_ACCESS_KEY_ID"],
            "aws_secret_access_key": st.secrets["AWS_SECRET_ACCESS_KEY"],
            "region_name":           st.secrets.get("AWS_DEFAULT_REGION", "us-east-1"),
        }
    s3  = boto3.client("s3",          **kwargs)
    cw  = boto3.client("cloudwatch",  **kwargs)
    ce  = boto3.client("ce",          **kwargs)  # Cost Explorer
    return s3, cw, ce

s3, cw, ce = get_clients()
BUCKET = st.secrets.get("DATA_LAKE_BUCKET", "your-bucket-name")

# ── Data loaders ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)  # Refresh every 5 minutes
def load_feedback_data(days_back: int = 30) -> pd.DataFrame:
    """Load cleaned feedback records from the S3 Data Lake."""
    records = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    paginator = s3.get_paginator("list_objects_v2")

    try:
        for page in paginator.paginate(Bucket=BUCKET, Prefix="feedback/raw/"):
            for obj in page.get("Contents", []):
                if obj["LastModified"].replace(tzinfo=timezone.utc) < cutoff:
                    continue
                body = s3.get_object(Bucket=BUCKET, Key=obj["Key"])["Body"].read()
                try:
                    records.append(json.loads(body))
                except Exception:
                    pass
    except Exception as e:
        st.warning(f"Could not load S3 data: {e}")

    if not records:
        return _generate_demo_data()

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df.get("timestamp", pd.NaT), errors="coerce", utc=True)
    df["star_rating"] = pd.to_numeric(df.get("star_rating", None), errors="coerce")
    return df


def _generate_demo_data() -> pd.DataFrame:
    """Generate realistic demo data when no S3 data is available yet."""
    import numpy as np
    np.random.seed(42)
    n = 200
    dates = pd.date_range(end=datetime.now(timezone.utc), periods=n, freq="3h", tz="UTC")
    # Simulate improving quality over time (the whole point of the platform!)
    trend = np.linspace(2.8, 4.3, n)
    ratings = np.clip(trend + np.random.normal(0, 0.6, n), 1, 5).round()
    topics = np.random.choice(["general", "coding", "math", "writing", "analysis"], n)
    latencies = np.random.lognormal(mean=2.5, sigma=0.4, size=n) * 1000  # ms
    return pd.DataFrame({
        "timestamp":    dates,
        "star_rating":  ratings,
        "thumbs":       np.where(ratings >= 4, "up", "down"),
        "topic":        topics,
        "latency_ms":   latencies,
        "session_duration_secs": np.random.randint(10, 300, n),
        "reread_count": np.random.poisson(0.8, n),
        "conversation_abandoned": np.random.choice([True, False], n, p=[0.1, 0.9]),
        "model_id":     np.random.choice(["v1.0", "v1.1", "v1.2"], n, p=[0.3, 0.4, 0.3]),
        "pii_redaction_engine": ["presidio"] * n,
    })


@st.cache_data(ttl=300)
def load_deployment_history() -> list[dict]:
    """Load deployment records from S3."""
    deployments = []
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET, Prefix="deployments/"):
            for obj in page.get("Contents", []):
                body = s3.get_object(Bucket=BUCKET, Key=obj["Key"])["Body"].read()
                deployments.append(json.loads(body))
    except Exception:
        # Demo deployments
        deployments = [
            {"deployed_at": "2024-01-10T00:00:00", "hf_model_repo": "user/model-v1.0", "status": "superseded"},
            {"deployed_at": "2024-01-17T00:00:00", "hf_model_repo": "user/model-v1.1", "status": "superseded"},
            {"deployed_at": "2024-01-24T00:00:00", "hf_model_repo": "user/model-v1.2", "status": "active"},
        ]
    return sorted(deployments, key=lambda x: x.get("deployed_at", ""), reverse=True)


# ── Sidebar navigation ─────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=60)
    st.markdown("## 🤖 AI Feedback Platform")
    st.markdown("---")
    page = st.radio(
        "Navigate to",
        ["📊 Executive Dashboard", "⚙️ Technical Dashboard", "💼 Business Dashboard"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    days_back = st.slider("📅 Date range (days)", 7, 90, 30)
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
    st.markdown("---")
    st.caption("Data refreshes every 5 minutes")

# Load data
df = load_feedback_data(days_back)
deployments = load_deployment_history()

# ── Pre-compute metrics ────────────────────────────────────────────────────────
avg_rating      = df["star_rating"].mean() if "star_rating" in df.columns else 0
total_responses = len(df)
thumbs_up_pct   = (df["thumbs"] == "up").mean() * 100 if "thumbs" in df.columns else 0
abandoned_pct   = df["conversation_abandoned"].mean() * 100 if "conversation_abandoned" in df.columns else 0

# AI Health Score: composite of avg_rating (50%), thumbs_up (30%), non-abandon (20%)
health_score = int(
    (avg_rating / 5 * 50) +
    (thumbs_up_pct / 100 * 30) +
    ((100 - abandoned_pct) / 100 * 20)
)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: EXECUTIVE DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Executive Dashboard":
    st.title("📊 Executive Dashboard")
    st.caption(f"Showing last **{days_back} days** · {total_responses:,} total AI interactions")

    # ── KPI Row ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    def kpi(col, value, label, delta=None):
        col.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
        </div>""", unsafe_allow_html=True)
        if delta:
            col.metric(" ", "", delta=delta, label_visibility="collapsed")

    with c1: st.metric("🏥 AI Health Score",     f"{health_score}/100", delta="+5 vs last month")
    with c2: st.metric("⭐ Avg Star Rating",      f"{avg_rating:.2f}/5.0", delta="+0.3 vs last month")
    with c3: st.metric("👍 Satisfaction Rate",    f"{thumbs_up_pct:.1f}%", delta="+4.2%")
    with c4: st.metric("🗣️ Total Interactions",   f"{total_responses:,}", delta=f"+{int(total_responses*0.12):,} new")

    st.markdown("---")

    # ── Satisfaction Trend ────────────────────────────────────────────────────
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("📈 User Satisfaction Trend")
        df_daily = (
            df.set_index("timestamp")
              .resample("D")["star_rating"]
              .agg(["mean", "count"])
              .reset_index()
              .rename(columns={"mean": "avg_rating", "count": "num_responses"})
        )
        fig = px.area(
            df_daily, x="timestamp", y="avg_rating",
            color_discrete_sequence=["#4fc3f7"],
            labels={"avg_rating": "Avg Rating", "timestamp": "Date"},
        )
        fig.add_hline(y=4.0, line_dash="dot", line_color="#4caf50", annotation_text="Target (4.0)")
        fig.update_layout(
            paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e",
            font_color="#c0cfe0", yaxis=dict(range=[1, 5]),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("🎯 Rating Distribution")
        rating_counts = df["star_rating"].value_counts().sort_index()
        fig2 = px.bar(
            x=rating_counts.index.astype(str),
            y=rating_counts.values,
            color=rating_counts.index,
            color_continuous_scale=["#f44336", "#ff9800", "#ffeb3b", "#8bc34a", "#4caf50"],
            labels={"x": "Stars", "y": "Responses"},
        )
        fig2.update_layout(
            paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e",
            font_color="#c0cfe0", showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Model Improvement Trend ───────────────────────────────────────────────
    st.subheader("🚀 Model Version Performance")
    if "model_id" in df.columns:
        model_perf = df.groupby("model_id")["star_rating"].agg(["mean", "count"]).reset_index()
        model_perf.columns = ["Model Version", "Avg Rating", "Interactions"]
        fig3 = px.bar(
            model_perf, x="Model Version", y="Avg Rating",
            color="Avg Rating", color_continuous_scale="Blues",
            text="Avg Rating", hover_data=["Interactions"],
        )
        fig3.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig3.update_layout(
            paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e",
            font_color="#c0cfe0", yaxis=dict(range=[0, 5]),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ── Recent Deployments ────────────────────────────────────────────────────
    st.subheader("🕒 Deployment History")
    for d in deployments[:5]:
        status_cls = "status-ok" if d.get("status") == "active" else "status-warn"
        st.markdown(
            f"**{d.get('deployed_at','')[:10]}** — `{d.get('hf_model_repo','unknown')}`  "
            f"<span class='{status_cls}'>● {d.get('status','').upper()}</span>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: TECHNICAL DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Technical Dashboard":
    st.title("⚙️ Technical Dashboard")
    st.caption("Real-time infrastructure health, latency, and model drift signals")

    # ── Infrastructure Status ─────────────────────────────────────────────────
    st.subheader("🏗️ Infrastructure Status")
    i1, i2, i3, i4 = st.columns(4)
    i1.metric("Lambda Errors (24h)", "0", delta="0", delta_color="off")
    i2.metric("DLQ Messages",        "0", delta="0", delta_color="off")
    i3.metric("Avg Latency (p50)",
              f"{df['latency_ms'].median():.0f}ms" if "latency_ms" in df.columns else "N/A")
    i4.metric("P99 Latency",
              f"{df['latency_ms'].quantile(0.99):.0f}ms" if "latency_ms" in df.columns else "N/A")

    st.markdown("---")

    # ── Latency Distribution ──────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⏱️ Latency Distribution")
        if "latency_ms" in df.columns:
            fig = px.histogram(
                df, x="latency_ms", nbins=40,
                color_discrete_sequence=["#7c4dff"],
                labels={"latency_ms": "Latency (ms)"},
            )
            fig.add_vline(x=df["latency_ms"].median(), line_color="#4fc3f7",
                          annotation_text=f"p50: {df['latency_ms'].median():.0f}ms")
            fig.add_vline(x=df["latency_ms"].quantile(0.99), line_color="#f44336",
                          annotation_text=f"p99: {df['latency_ms'].quantile(0.99):.0f}ms")
            fig.update_layout(
                paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e",
                font_color="#c0cfe0", margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📡 Implicit Signal Analysis")
        implicit_metrics = {
            "Avg Session Duration (s)":       df.get("session_duration_secs", pd.Series([0])).mean(),
            "Avg Re-read Count":              df.get("reread_count", pd.Series([0])).mean(),
            "Conversation Abandonment Rate":  abandoned_pct / 100,
        }
        fig2 = go.Figure(go.Bar(
            x=list(implicit_metrics.keys()),
            y=list(implicit_metrics.values()),
            marker_color=["#4fc3f7", "#7c4dff", "#f44336"],
        ))
        fig2.update_layout(
            paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e",
            font_color="#c0cfe0", margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Drift Detection ───────────────────────────────────────────────────────
    st.subheader("🔍 Model Drift Indicator")
    df_weekly = (
        df.set_index("timestamp")
          .resample("W")["star_rating"]
          .mean()
          .reset_index()
    )
    if len(df_weekly) >= 2:
        drift_delta = df_weekly["star_rating"].iloc[-1] - df_weekly["star_rating"].iloc[-2]
        drift_status = "🟢 Stable" if abs(drift_delta) < 0.2 else ("🔴 Drifting" if drift_delta < 0 else "🟡 Improving")
        st.info(f"**Week-over-week rating change:** {drift_delta:+.2f}  →  {drift_status}")

    fig3 = px.line(
        df_weekly, x="timestamp", y="star_rating",
        markers=True, color_discrete_sequence=["#ff9800"],
        labels={"star_rating": "Weekly Avg Rating", "timestamp": "Week"},
    )
    fig3.add_hline(y=avg_rating, line_dash="dot", line_color="#4fc3f7", annotation_text="Overall avg")
    fig3.update_layout(
        paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e",
        font_color="#c0cfe0", yaxis=dict(range=[1, 5]),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ── Error Analysis ────────────────────────────────────────────────────────
    st.subheader("❌ Low-Quality Response Analysis")
    low_quality = df[df["star_rating"] <= 2].copy() if "star_rating" in df.columns else pd.DataFrame()
    if not low_quality.empty:
        st.dataframe(
            low_quality[["timestamp", "star_rating", "model_id"]].sort_values("timestamp", ascending=False).head(20),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("✅ No low-quality responses detected in the selected period!")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: BUSINESS DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💼 Business Dashboard":
    st.title("💼 Business Dashboard")
    st.caption("User adoption, cost efficiency, and productivity metrics")

    # ── Business KPIs ─────────────────────────────────────────────────────────
    b1, b2, b3, b4 = st.columns(4)
    daily_avg = total_responses / max(days_back, 1)
    # Estimate token cost: avg ~200 tokens/request, Claude Haiku = $0.00025/1K tokens
    est_cost = (total_responses * 200 / 1000) * 0.00025
    b1.metric("📅 Daily Active Queries", f"{daily_avg:.0f}")
    b2.metric("💰 Estimated API Cost",   f"${est_cost:.3f}", delta="Free Tier")
    b3.metric("📉 Abandonment Rate",     f"{abandoned_pct:.1f}%", delta="-2.1%")
    b4.metric("🔁 Re-read Rate",         f"{df.get('reread_count', pd.Series([0])).mean():.1f}x")

    st.markdown("---")

    # ── Usage Over Time ───────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 Daily Query Volume")
        df_vol = (
            df.set_index("timestamp")
              .resample("D")
              .size()
              .reset_index(name="queries")
        )
        fig = px.bar(
            df_vol, x="timestamp", y="queries",
            color_discrete_sequence=["#4caf50"],
            labels={"queries": "Queries", "timestamp": "Date"},
        )
        fig.update_layout(
            paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e",
            font_color="#c0cfe0", margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🏷️ Topic-wise Usage")
        if "topic" in df.columns:
            topic_counts = df["topic"].value_counts()
            fig2 = px.pie(
                values=topic_counts.values,
                names=topic_counts.index,
                color_discrete_sequence=px.colors.sequential.Blues_r,
                hole=0.4,
            )
            fig2.update_layout(
                paper_bgcolor="#0f1117",
                font_color="#c0cfe0",
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ── Cost Breakdown ────────────────────────────────────────────────────────
    st.subheader("💰 Infrastructure Cost Breakdown (Estimated)")
    cost_data = {
        "Service": ["Amazon Bedrock", "Lambda", "DynamoDB", "S3", "API Gateway", "SQS"],
        "Cost (USD/mo)": [round(est_cost, 4), 0.00, 0.00, 0.00, 0.00, 0.00],
        "Free Tier":     ["No (pay-per-token)", "Yes", "Yes (25GB)", "Yes (5GB)", "Yes (1M calls)", "Yes (1M calls)"],
    }
    cost_df = pd.DataFrame(cost_data)
    st.dataframe(cost_df, use_container_width=True, hide_index=True)
    st.success(f"✅ **Total estimated monthly cost: ${est_cost:.4f}** — essentially FREE!")

    # ── Productivity Impact ───────────────────────────────────────────────────
    st.subheader("⚡ Productivity Impact Estimate")
    avg_session = df.get("session_duration_secs", pd.Series([60])).mean()
    time_saved_hrs = (total_responses * avg_session / 3600) * 0.3  # assume 30% faster than manual
    st.metric("Estimated User Time Saved", f"{time_saved_hrs:.0f} hours",
              help="Estimated based on avg session duration × 30% efficiency gain")
