# dashboard.py — Aha CRM (Premium Final Version)

import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Aha CRM",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🎨 Premium Palette
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
.stApp {{
    background-color: {BG};
}}

html, body, [class*="st-"] {{
    font-family: 'Inter', sans-serif;
    color: #f1f5f9;
}}

div[data-testid="stMetric"] {{
    background: {CARD};
    padding: 26px !important;
    border-radius: 18px;
    border: 1px solid {BORDER};
    transition: all 0.25s ease;
}}

div[data-testid="stMetric"]:hover {{
    transform: translateY(-6px);
    border-color: {PRIMARY};
    box-shadow: 0 0 25px rgba(139,92,246,0.15);
}}

hr {{
    border-top: 1px solid {BORDER};
}}

.stButton > button {{
    background: linear-gradient(135deg, {PRIMARY}, #6366f1);
    border: none;
    border-radius: 10px;
    padding: 0.6rem 1.5rem;
    font-weight: 600;
    color: white;
}}
.stButton > button:hover {{
    transform: scale(1.05);
}}

#MainMenu, footer, header {{
    visibility: hidden;
}}
</style>
""", unsafe_allow_html=True)

# =====================================================
# SESSION STATE
# =====================================================
if "last_pull" not in st.session_state:
    st.session_state.last_pull = None

# =====================================================
# SUPABASE
# =====================================================
def get_client():
    dotenv_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    else:
        load_dotenv()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        st.error("Missing Supabase credentials")
        st.stop()

    return create_client(url, key)

@st.cache_data(ttl=600)
def fetch_table(table):
    client = get_client()
    res = client.table(table).select("*").execute()
    return pd.DataFrame(res.data)

def fetch_metrics():
    client = get_client()
    res = client.table("daily_metrics_summary").select("*").execute()
    return pd.DataFrame(res.data)

def refresh():
    st.cache_data.clear()
    
    # Trigger the backend pipeline (npm run start:pipeline equivalent)
    with st.spinner("🔄 Synchronizing with Zoho & Running AI Analysis..."):
        try:
            # This now waits for the backend to finish (see aiRoutes.js change)
            requests.post("http://localhost:3001/api/ai/trigger", timeout=120)
            st.success("✅ Dashboard Synchronized")
        except Exception as e:
            st.error(f"❌ Sync failed: {e}")
        
    st.session_state.last_pull = datetime.now()

# =====================================================
# HEADER
# =====================================================
col1, col2 = st.columns([8,2])

with col1:
    st.markdown("## 💠 Aha CRM")

with col2:
    if st.button("🔄 Refresh"):
        refresh()
        st.success("Data refreshed")

    if st.session_state.last_pull:
        st.caption(f"Last pulled: {st.session_state.last_pull.strftime('%Y-%m-%d %H:%M:%S')}")

st.divider()

# =====================================================
# LOAD DATA
# =====================================================
leads = fetch_table("crm_leads")
deals = fetch_table("crm_deals")
ai_summary = fetch_table("ai_summaries")
metrics = fetch_metrics()

if st.session_state.last_pull is None:
    st.session_state.last_pull = datetime.now()

# =====================================================
# TOP STRATEGIC KPIs
# =====================================================
if not metrics.empty:
    m = metrics.iloc[0]

    k1, k2, k3, k4 = st.columns(4)

    k1.metric("Today's New Leads", int(m["new_leads_today"]))
    k2.metric("Qualified Leads", int(m["qualified_leads"]))
    k3.metric("Deals Closed", int(m["deals_closed"]))
    k4.metric("Total Revenue", f"₹ {float(m.get('total_revenue',0)):,.0f}")

st.divider()

# =====================================================
# LEADS THIS MONTH
# =====================================================
st.subheader("📈 Leads This Month")

if not leads.empty:
    leads["created_time"] = pd.to_datetime(leads["created_time"])

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

    daily.columns = ["date", "leads"]

    fig = px.area(
        daily,
        x="date",
        y="leads",
        color_discrete_sequence=[PRIMARY],
        template="plotly_dark"
    )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=10,r=10),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=GRID)
    )

    st.plotly_chart(fig, use_container_width=True)

st.divider()

# =====================================================
# LEAD SOURCE DISTRIBUTION (Improved)
# =====================================================
st.subheader("🎯 Lead Source Distribution")

if not leads.empty:

    source_dist = (
        leads["source"]
        .value_counts()
        .reset_index()
    )

    source_dist.columns = ["Source", "Count"]

    # Clean labels
    source_dist["Source"] = (
        source_dist["Source"]
        .str.replace("_", " ")
        .str.title()
    )

    # Keep Top 5, group rest as "Other"
    top_n = 5
    if len(source_dist) > top_n:
        top_sources = source_dist.head(top_n)
        others = pd.DataFrame({
            "Source": ["Other"],
            "Count": [source_dist["Count"][top_n:].sum()]
        })
        source_dist = pd.concat([top_sources, others], ignore_index=True)

    total_leads = source_dist["Count"].sum()

    fig = px.pie(
        source_dist,
        values="Count",
        names="Source",
        hole=0.65,
        color_discrete_sequence=[
            PRIMARY,
            SUCCESS,
            ACCENT,
            CYAN,
            DANGER,
            "#64748b"
        ],
        template="plotly_dark"
    )

    fig.update_traces(
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>Leads: %{value}<br>Share: %{percent}",
        marker=dict(line=dict(color=BG, width=2))
    )

    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1
        ),
        margin=dict(t=20, b=20, l=20, r=20),
        annotations=[
            dict(
                text=f"<b>{total_leads}</b><br>Total Leads",
                x=0.5,
                y=0.5,
                font_size=18,
                showarrow=False
            )
        ],
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# CONVERSION FUNNEL
# =====================================================
st.subheader("📊 Conversion Funnel")

if not deals.empty:
    # Sort stages in a logical sales order
    stage_order = [
        "Qualification", 
        "Needs Analysis", 
        "Value Proposition", 
        "Id. Decision Makers", 
        "Proposal/Price Quote", 
        "Negotiation/Review", 
        "Closed Won"
    ]
    
    pipeline = (
        deals.groupby("stage")
        .agg(Deals=("deal_id","count"),
             Revenue=("amount","sum"))
        .reset_index()
    )
    
    # Filter to only including known stages for a clean funnel, or just sort them
    pipeline["stage_idx"] = pipeline["stage"].apply(
        lambda x: stage_order.index(x) if x in stage_order else 99
    )
    pipeline = pipeline.sort_values("stage_idx")

    fig = px.funnel(
        pipeline,
        y="stage",
        x="Deals",
        color="Revenue",
        color_continuous_scale=[[0,CARD],[1,SUCCESS]],
        template="plotly_dark"
    )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False,
        yaxis=dict(title="")
    )

    fig.update_traces(
        textinfo="value+percent initial",
        hovertemplate="Stage: %{y}<br>Deals: %{x}<br>Revenue: ₹ %{customdata[0]:,.0f}",
        customdata=pipeline[["Revenue"]]
    )

    st.plotly_chart(fig, use_container_width=True)

st.divider()

# =====================================================
# REVENUE BY OWNER
# =====================================================
st.subheader("💰 Revenue by Owner")

if not deals.empty:
    deals["stage"] = deals["stage"].astype(str)
    won = deals[deals["stage"].str.contains("closed won",case=False,na=False)]

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

        fig.update_traces(
            hovertemplate="Owner: %{x}<br>Revenue: ₹ %{y:,.0f}"
        )

        st.plotly_chart(fig, use_container_width=True)

st.divider()

# =====================================================
# AI EXECUTIVE INSIGHTS
# =====================================================
st.subheader("🧠 AI Executive Insights")

if not ai_summary.empty:
    latest = ai_summary.sort_values("created_at",ascending=False).iloc[0]
    payload = latest["payload"]
    summary = payload.get("aiSummary",{}).get("text","No summary available")

    st.markdown(f"""
    <div style="
        background:{CARD};
        padding:28px;
        border-radius:18px;
        border:1px solid {BORDER};
        line-height:1.7;
        font-size:15px;">
        <strong>📌 Strategic Insight</strong><br><br>
        {summary}
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("No AI insights available.")