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
    page_title="Aha CRM | Intelligence",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Colors
PRIMARY = "#8b5cf6" # Violet
SECONDARY = "#6366f1" # Indigo
SUCCESS = "#10b981" # Emerald
ACCENT = "#f59e0b" # Amber
DANGER = "#f43f5e" # Rose
CYAN = "#06b6d4" # Cyan
BG = "#020617" # Deep Navy
CARD = "rgba(15, 23, 42, 0.7)" # Glassmorphism base
BORDER = "rgba(255,255,255,0.08)"
GRID = "rgba(255,255,255,0.03)"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

.stApp {{ background-color: {BG}; }}
html, body, [class*="st-"] {{
    font-family: 'Inter', sans-serif;
    color:#f1f5f9;
}}

/* Glassmorphism Cards */
div[data-testid="stMetric"] {{
    background:{CARD}!important;
    backdrop-filter: blur(12px);
    padding: 24px!important;
    border-radius: 16px;
    border: 1px solid {BORDER};
    box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.2);
    transition: all 0.3s ease;
}}
div[data-testid="stMetric"]:hover {{
    border-color: {PRIMARY};
    transform: translateY(-2px);
    box-shadow: 0 10px 30px -5px rgba(139, 92, 246, 0.2);
}}

/* Sidebar and Header Hiding */
#MainMenu, footer, header {{ visibility:hidden; }}

/* Custom Header Gradient */
.header-text {{
    background: linear-gradient(90deg, #fff 0%, {PRIMARY} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
}}

/* Metrics Delta Styling */
[data-testid="stMetricDelta"] > div {{
    font-weight: 600;
}}
</style>
""", unsafe_allow_html=True)

# =====================================================
# SUPABASE & HELPERS
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
    try:
        data = get_client().table(table).select("*").execute().data
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching {table}: {e}")
        return pd.DataFrame()

def fetch_metrics():
    client = get_client()
    res = client.table("daily_metrics_summary").select("*").limit(1).execute()
    return pd.DataFrame(res.data)

def refresh():
    st.cache_data.clear()
    with st.spinner("🔄 Synchronizing Intelligence..."):
        try:
            requests.post("http://localhost:3001/api/ai/trigger", timeout=120)
            st.success("✅ Dashboard Synchronized")
        except:
            st.warning("⚠️ Backend trigger timed out or unreachable, but data may still reload.")
    st.session_state.last_pull = datetime.now()

# =====================================================
# HEADER
# =====================================================
col1, col2 = st.columns([8,2])
col1.markdown("<h1 class='header-text'>💠 Aha CRM Intelligence</h1>", unsafe_allow_html=True)

if col2.button("🔄 Force Sync AI", use_container_width=True):
    refresh()

if "last_pull" not in st.session_state:
    st.session_state.last_pull = datetime.now()

col2.caption(
    f"Last synchronized: {st.session_state.last_pull.strftime('%H:%M:%S')}"
)

st.divider()

# =====================================================
# LOAD DATA
# =====================================================
leads = fetch_table("crm_leads")
deals = fetch_table("crm_deals")
ai_summary_table = fetch_table("ai_summaries")
metrics = fetch_metrics()

if not leads.empty:
    leads["created_time"] = pd.to_datetime(leads["created_time"])

if not deals.empty:
    deals["created_time"] = pd.to_datetime(deals["created_time"])
    deals["stage"] = deals["stage"].astype(str)
    deals["amount"] = pd.to_numeric(deals["amount"], errors="coerce").fillna(0)

# Get latest AI Payload
ai_payload = {}
if not ai_summary_table.empty:
    latest_ai = ai_summary_table.sort_values("created_at", ascending=False).iloc[0]
    ai_payload = latest_ai.get("payload", {})

# =====================================================
# MAIN TABS
# =====================================================
tab_today, tab_pipeline, tab_ai = st.tabs([
    "📅 Today's Strategic Pulse", 
    "📊 Cumulative Pipeline", 
    "🧠 AI Executive Insights"
])

# -----------------------------------------------------
# TAB: TODAY
# -----------------------------------------------------
with tab_today:
    st.markdown("### ⚡ Critical Metrics")
    
    # Use AI Payload for Deltas if available
    overview = ai_payload.get("overview", {})
    
    k1, k2, k3, k4 = st.columns(4)
    
    def display_metric(col, label, key, default_val, prefix="", suffix=""):
        data = overview.get(key, {})
        val = data.get("value", default_val)
        delta = data.get("changePct", 0)
        trend = data.get("trendStr", "")
        
        # Format display
        display_val = f"{prefix}{val}{suffix}"
        
        col.metric(
            label=label,
            value=display_val,
            delta=f"{delta}% {trend}" if delta != 0 else None,
            delta_color="normal" if data.get("isGood", True) else "inverse"
        )

    if not metrics.empty:
        m = metrics.iloc[0]
        display_metric(k1, "Today's New Leads", "newLeads", int(m["new_leads_today"]))
        display_metric(k2, "Today's Conversion Rate", "conversionRate", "0%", suffix="")
        display_metric(k3, "Deals Closed (Won)", "dealsClosed", int(m["deals_closed"]))
        display_metric(k4, "Revenue (Won Today)", "pipelineValue", f"₹ {float(m.get('deal_amount_won',0)):,.0f}")
    else:
        st.info("No daily metrics available. Click 'Force Sync AI' to synchronize.")

    st.divider()
    
    # Lead Lifecycle Metrics
    st.markdown("#### 🔄 Lead Lifecycle")
    if not metrics.empty:
        m = metrics.iloc[0]
        l1, l2, l3, l4 = st.columns(4)
        l1.metric("Contacted", int(m.get("leads_contacted", 0)))
        l2.metric("Qualified", int(m.get("qualified_leads", 0)))
        l3.metric("Demos Scheduled", int(m.get("demos_scheduled", 0)))
        l4.metric("Proposals Sent", int(m.get("proposals_sent", 0)))

        st.divider()
        
        # Today's Revenue Loss/Total
        r1, r2 = st.columns(2)
        r1.metric("Revenue Lost Today", f"₹ {float(m.get('deal_amount_lost',0)):,.0f}")
        r2.metric("Negotiations Active", int(m.get("negotiations_active", 0)))

# -----------------------------------------------------
# TAB: PIPELINE
# -----------------------------------------------------
with tab_pipeline:
    st.markdown("### 📊 High-Resolution Conversion Funnel")
    
    if not leads.empty:
        # Consolidated High-Res Funnel (from metrics.js logic)
        total_leads = len(leads)
        
        if not deals.empty:
            # We fetch pre-calculated funnel if possible, or build it
            # For simplicity and accuracy with backend, we use the backend logic
            # Stages: New Leads -> Contacted -> Qualified -> Proposal Sent -> Negotiation -> Won
            
            won_deals = deals[deals["stage"].str.contains("closed won", case=False, na=False)]
            negotiation_deals = deals[deals["stage"].str.contains("negotiation/review", case=False, na=False)]
            proposal_deals = deals[deals["stage"].str.contains("proposal shared", case=False, na=False)]
            
            funnel_data = [
                {"Stage": "Total Leads", "Count": total_leads},
                {"Stage": "Contacted", "Count": len(deals)}, # Deals exist
                {"Stage": "Qualified", "Count": len(deals[deals["stage"].str.contains("Awaiting Electric Plan", case=False, na=False)]) + len(proposal_deals) + len(negotiation_deals) + len(won_deals)},
                {"Stage": "Proposal Shared", "Count": len(proposal_deals) + len(negotiation_deals) + len(won_deals)},
                {"Stage": "Negotiation", "Count": len(negotiation_deals) + len(won_deals)},
                {"Stage": "Closed Won", "Count": len(won_deals)}
            ]
            
            df_funnel = pd.DataFrame(funnel_data)
            fig = px.funnel(
                df_funnel, x="Count", y="Stage",
                color_discrete_sequence=[PRIMARY],
                template="plotly_dark"
            )
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("#### 🎯 Lead Source Distribution")
        if not leads.empty:
            source_dist = leads["source"].value_counts().reset_index()
            source_dist.columns = ["Source", "Count"]
            source_dist["Source"] = source_dist["Source"].str.replace("_", " ").str.title()
            
            fig = px.pie(
                source_dist.head(6), values="Count", names="Source",
                hole=0.6,
                color_discrete_sequence=[PRIMARY, SUCCESS, ACCENT, CYAN, DANGER, SECONDARY],
                template="plotly_dark"
            )
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("#### 💰 Revenue by Owner")
        if not deals.empty:
            won = deals[deals["stage"].str.contains("closed won", case=False)]
            if not won.empty:
                owner_rev = won.groupby("owner_name")["amount"].sum().reset_index().sort_values("amount", ascending=False)
                fig = px.bar(
                    owner_rev, x="owner_name", y="amount",
                    color_discrete_sequence=[SUCCESS],
                    template="plotly_dark"
                )
                fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", yaxis=dict(gridcolor=GRID))
                st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------
# TAB: AI INSIGHTS
# -----------------------------------------------------
with tab_ai:
    st.markdown("### 🧠 Executive Revenue Intelligence")
    
    if ai_payload:
        summary = ai_payload.get("aiSummary", {}).get("text", "No summary available.")
        viz_insight = ai_payload.get("vizInsights", {}).get("text", "")
        
        # Display Summary
        st.markdown(f"""
        <div style="background:{CARD}; padding:30px; border-radius:18px; border:1px solid {BORDER}; line-height:1.8; margin-bottom:20px;">
            <h4 style="color:{PRIMARY}; margin-top:0;">📋 Strategic Briefing</h4>
            {summary}
        </div>
        """, unsafe_allow_html=True)
        
        if viz_insight:
            st.markdown(f"""
            <div style="background:{CARD}; padding:25px; border-radius:18px; border:1px solid {BORDER}; border-left:4px solid {ACCENT};">
                <h5 style="color:{ACCENT}; margin-top:0;">💡 Visualization Insight</h5>
                {viz_insight}
            </div>
            """, unsafe_allow_html=True)
            
        # Last Run
        run_time = ai_payload.get("aiSummary", {}).get("lastRunTime", "Recently")
        st.caption(f"Intelligence generated at: {run_time}")
    else:
        st.info("No AI insights generated yet. Use 'Force Sync AI' to trigger the analysis pipeline.")

# =====================================================
# FOOTER (Hidden in CSS but status for dev)
# =====================================================
if not ai_payload and not metrics.empty:
    st.warning("⚠️ Metrics are loaded but AI analysis (deltas/insights) hasn't run for this data yet.")