# dashboard.py — Aha CRM (Complete + Today's Leads Added)

import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Aha CRM",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

PRIMARY = "#8b5cf6"
SUCCESS = "#10b981"
ACCENT = "#f59e0b"
DANGER = "#f43f5e"
CYAN = "#06b6d4"

BG = "#020617"
CARD = "#0f172a"
BORDER = "rgba(255,255,255,0.08)"
GRID = "rgba(255,255,255,0.05)"

st.markdown(f"""
<style>
.stApp {{ background-color: {BG}; }}
html, body, [class*="st-"] {{
    font-family: 'Inter', sans-serif;
    color:#f1f5f9;
}}
div[data-testid="stMetric"] {{
    background:{CARD};
    padding:26px!important;
    border-radius:18px;
    border:1px solid {BORDER};
}}
div[data-testid="stMetric"]:hover {{
    border-color:{PRIMARY};
    box-shadow:0 0 25px rgba(139,92,246,0.15);
}}
hr {{ border-top:1px solid {BORDER}; }}
#MainMenu, footer, header {{ visibility:hidden; }}
</style>
""", unsafe_allow_html=True)

# =====================================================
# SUPABASE
# =====================================================
def get_client():
    dotenv_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    else:
        load_dotenv()
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"]
    )

@st.cache_data(ttl=60)
def fetch_table(table):
    return pd.DataFrame(
        get_client().table(table).select("*").execute().data
    )

def fetch_metrics():
    client = get_client()
    # Explicitly fetch the single row of pre-calculated backend metrics
    res = client.table("daily_metrics_summary").select("*").limit(1).execute()
    return pd.DataFrame(res.data)

def refresh():
    st.cache_data.clear()
    with st.spinner("🔄 Synchronizing Backend + AI..."):
        try:
            requests.post("http://localhost:3001/api/ai/trigger", timeout=120)
            st.success("✅ Dashboard Synchronized")
        except:
            st.error("❌ Backend not reachable")
    st.session_state.last_pull = datetime.now()

# =====================================================
# HEADER
# =====================================================
col1, col2 = st.columns([8,2])
col1.markdown("## 💠 Aha CRM")

if col2.button("🔄 Refresh"):
    refresh()

if "last_pull" not in st.session_state:
    st.session_state.last_pull = datetime.now()

col2.caption(
    f"Last pulled: {st.session_state.last_pull.strftime('%Y-%m-%d %H:%M:%S')}"
)

st.divider()

# =====================================================
# LOAD DATA
# =====================================================
leads = fetch_table("crm_leads")
deals = fetch_table("crm_deals")
ai_summary = fetch_table("ai_summaries")
metrics = fetch_metrics()

if not leads.empty:
    leads["created_time"] = pd.to_datetime(leads["created_time"])

if not deals.empty:
    deals["created_time"] = pd.to_datetime(deals["created_time"])
    deals["stage"] = deals["stage"].astype(str)
    deals["amount"] = pd.to_numeric(deals["amount"], errors="coerce").fillna(0)

# =====================================================
# 🔥 TODAY'S PERFORMANCE
# =====================================================
st.markdown(
    "### 📅 Today's Strategic Pulse "
    "<span style='font-size:14px;color:#94a3b8;'>(Daily)</span>",
    unsafe_allow_html=True
)

if not metrics.empty:
    # Get the latest verified summary from the backend
    m = metrics.iloc[0]
    
    k1, k2, k3, k4 = st.columns(4)
    
    # These match the backend sync logic exactly
    k1.metric("Today's New Leads", int(m["new_leads_today"]))
    k2.metric("Qualified Leads", int(m["qualified_leads"]))
    k3.metric("Deals Closed (Won)", int(m["deals_closed"]))
    k4.metric("Revenue (Won Today)", f"₹ {float(m.get('deal_amount_won',0)):,.0f}")
else:
    st.info("No daily metrics available. Click Refresh to synchronize.")

st.divider()

# =====================================================
# TOTAL PIPELINE OVERVIEW
# =====================================================
st.markdown(
    "### 📊 Cumulative Pipeline "
    "<span style='font-size:14px;color:#94a3b8;'>(All Time)</span>",
    unsafe_allow_html=True
)

if not leads.empty and not deals.empty:
    total_leads = len(leads)
    
    # Active pipeline: Sum of amounts where stage is not Closed Won or Closed Lost
    active_deals = deals[~deals["stage"].str.contains("closed", case=False)]
    pipeline_value = active_deals["amount"].sum()
    
    # Total Revenue: Only Closed Won deals
    won_deals = deals[deals["stage"].str.contains("closed won", case=False)]
    total_revenue_won = won_deals["amount"].sum()
    
    # Historical Win Rate (by Deal Count)
    total_closed = deals[deals["stage"].str.contains("closed", case=False)]
    won_count = len(won_deals)
    win_rate = (won_count / len(total_closed) * 100) if len(total_closed) > 0 else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Lifetime Leads", total_leads)
    k2.metric("Open Pipeline Value", f"₹ {pipeline_value:,.0f}")
    k3.metric("Total Revenue Won", f"₹ {total_revenue_won:,.0f}")
    k4.metric("Win Rate (%)", f"{win_rate:.1f}%")

st.divider()

# =====================================================
# LEADS THIS MONTH (Trend)
# =====================================================
st.markdown(
    "### 📈 Leads This Month "
    "<span style='font-size:14px;color:#94a3b8;'>(Monthly)</span>",
    unsafe_allow_html=True
)

if not leads.empty:
    now = datetime.now()

    month_data = leads[
        (leads["created_time"].dt.month == now.month) &
        (leads["created_time"].dt.year == now.year)
    ]

    daily = (
        month_data.groupby(month_data["created_time"].dt.date)
        .size()
        .reset_index(name="leads")
    )

    fig = px.area(
        daily,
        x="created_time",
        y="leads",
        color_discrete_sequence=[PRIMARY],
        template="plotly_dark"
    )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor=GRID)
    )

    st.plotly_chart(fig, use_container_width=True)

st.divider()

# =====================================================
# LEADS BY SOURCE
# =====================================================
st.markdown(
    "### 🎯 Lead Source Distribution "
    "<span style='font-size:14px;color:#94a3b8;'>(All Time)</span>",
    unsafe_allow_html=True
)

if not leads.empty:
    source_dist = leads["source"].value_counts().reset_index()
    source_dist.columns = ["Source", "Count"]
    
    # Keep Top 5
    top_n = 5
    if len(source_dist) > top_n:
        top_sources = source_dist.head(top_n)
        others = pd.DataFrame({
            "Source": ["Other"],
            "Count": [source_dist["Count"][top_n:].sum()]
        })
        source_dist = pd.concat([top_sources, others], ignore_index=True)

    fig = px.pie(
        source_dist,
        values="Count",
        names="Source",
        hole=0.6,
        color_discrete_sequence=[PRIMARY, SUCCESS, ACCENT, CYAN, DANGER],
        template="plotly_dark"
    )
    
    fig.update_layout(
        margin=dict(t=20, b=20, l=20, r=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# OPERATIONAL LEAK DETECTOR
# =====================================================
st.markdown(
    "### 🕵️‍♂️ Operational Leak Detector "
    "<span style='font-size:14px;color:#94a3b8;'>(Conversion Health)</span>",
    unsafe_allow_html=True
)

if not leads.empty:
    total_leads = len(leads)
    converted_leads = leads["is_converted"].sum()
    
    active_deals = 0
    won_deals = 0
    
    if not deals.empty:
        active_deals = len(deals[~deals["stage"].str.contains("closed", case=False)])
        won_deals = len(deals[deals["stage"].str.contains("closed won", case=False)])

    leak_data = pd.DataFrame({
        "Stage": ["Total Leads", "Converted Leads", "Active Deals", "Won Deals"],
        "Count": [total_leads, converted_leads, active_deals, won_deals]
    })

    fig = px.funnel(
        leak_data,
        x="Count",
        y="Stage",
        color_discrete_sequence=[ACCENT],
        template="plotly_dark"
    )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10)
    )
    
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# =====================================================
# CONVERSION FUNNEL
# =====================================================
st.markdown(
    "### 📊 Sales Conversion Funnel "
    "<span style='font-size:14px;color:#94a3b8;'>(All Time)</span>",
    unsafe_allow_html=True
)

if not leads.empty:
    # We use the verified stages from the brief
    stage_order = [
        "Qualification", 
        "Needs Analysis", 
        "Value Proposition", 
        "Id. Decision Makers", 
        "Proposal/Price Quote", 
        "Negotiation/Review", 
        "Closed Won"
    ]
    
    # Aggregate data
    pipeline = deals.groupby("stage").size().reset_index(name="Count")
    
    # Create a full sequence for the funnel
    funnel_data = []
    total_leads = len(leads)
    funnel_data.append({"Stage": "Total Leads", "Count": total_leads})
    
    for stage in stage_order:
        count = pipeline[pipeline["stage"] == stage]["Count"].sum()
        if count > 0 or stage == "Closed Won": # Ensure bottom of funnel shows
            funnel_data.append({"Stage": stage, "Count": count})
            
    df_funnel = pd.DataFrame(funnel_data)

    fig = px.funnel(
        df_funnel,
        x="Count",
        y="Stage",
        color_discrete_sequence=[PRIMARY],
        template="plotly_dark"
    )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# =====================================================
# PIPELINE VALUE SUMMARY
# =====================================================
st.markdown(
    "### 💰 Pipeline Value Summary "
    "<span style='font-size:14px;color:#94a3b8;'>(Current Status)</span>",
    unsafe_allow_html=True
)

if not deals.empty:
    open_deals = deals[~deals["stage"].str.contains("closed", case=False)]
    open_value = open_deals["amount"].sum()

    won_deals = deals[deals["stage"].str.contains("closed won", case=False)]
    won_value = won_deals["amount"].sum()

    lost_deals = deals[deals["stage"].str.contains("closed lost", case=False)]
    lost_value = lost_deals["amount"].sum()

    win_rate = (len(won_deals) / (len(won_deals) + len(lost_deals)) * 100) if (len(won_deals) + len(lost_deals)) > 0 else 0

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Open Pipeline", f"₹ {open_value:,.0f}")
    p2.metric("Revenue Won", f"₹ {won_value:,.0f}")
    p3.metric("Revenue Lost", f"₹ {lost_value:,.0f}")
    p4.metric("Win Rate (%)", f"{win_rate:.1f}%")

st.divider()

# =====================================================
# REVENUE BY OWNER
# =====================================================
st.markdown(
    "### 💰 Revenue by Owner "
    "<span style='font-size:14px;color:#94a3b8;'>(Closed Won)</span>",
    unsafe_allow_html=True
)

if not deals.empty:
    won = deals[
        deals["stage"].str.contains("closed won",case=False)
    ]

    if not won.empty:
        owner_rev = (
            won.groupby("owner_name")["amount"]
            .sum()
            .reset_index()
            .sort_values("amount",ascending=False)
        )

        fig = px.bar(
            owner_rev,
            x="owner_name",
            y="amount",
            color_discrete_sequence=[PRIMARY],
            template="plotly_dark"
        )

        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor=GRID)
        )

        st.plotly_chart(fig, use_container_width=True)

st.divider()

# =====================================================
# AI EXECUTIVE INSIGHTS
# =====================================================
st.markdown(
    "### 🧠 AI Executive Insights "
    "<span style='font-size:14px;color:#94a3b8;'>(Latest Analysis)</span>",
    unsafe_allow_html=True
)

if not ai_summary.empty:
    latest = ai_summary.sort_values(
        "created_at",ascending=False
    ).iloc[0]

    summary = latest["payload"].get(
        "aiSummary",{}
    ).get("text","")

    st.markdown(f"""
    <div style="background:{CARD};
                padding:28px;
                border-radius:18px;
                border:1px solid {BORDER};
                line-height:1.7;">
    <div style="font-size:12px;color:#94a3b8;margin-bottom:12px;">
        📅 Insight Generated: {latest['created_at']}
    </div>
    {summary}
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("No AI insights available.")