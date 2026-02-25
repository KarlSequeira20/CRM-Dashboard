# dashboard.py — Aha CRM Intelligence (Today's Pulse - Optimized)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, ClientOptions
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import json

# Silence Pandas downcasting warning
pd.set_option('future.no_silent_downcasting', True)

def refresh():
    st.cache_data.clear()
    try:
        # Call the backend sync trigger
        requests.post("http://localhost:3001/api/ai/trigger", timeout=5)
    except:
        pass

def human_format(num, is_currency=False):
    if num is None: return "0"
    prefix = "₹ " if is_currency else ""
    
    magnitude = 0
    while abs(num) >= 1000 and magnitude < 4:
        magnitude += 1
        num /= 1000.0
    
    suffix = ['', 'k', 'M', 'B', 'T'][magnitude]
    
    if magnitude == 0:
        return f"{prefix}{int(num):,}" if num % 1 == 0 else f"{prefix}{num:,.2f}"
    
    # 1.2k, 15.4M, etc.
    return f"{prefix}{num:.1f}{suffix}"

# =====================================================
# CONFIG & STYLING
# =====================================================
st.set_page_config(
    page_title="Aha CRM | Today's Intelligence",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

PRIMARY = "#8b5cf6"
SECONDARY = "#6366f1"
SUCCESS = "#10b981"
ACCENT = "#f59e0b"
DANGER = "#f43f5e"
CYAN = "#06b6d4"
BG = "#020617"
CARD_BG = "rgba(15, 23, 42, 0.6)"
BORDER = "rgba(255, 255, 255, 0.08)"
GRID = "rgba(255, 255, 255, 0.03)"

st.markdown(f"""
<style>
    .stApp {{ background-color: {BG}; }}
    html, body, [class*="st-"] {{
        font-family: 'Inter', -apple-system, sans-serif;
        color: #f1f5f9;
    }}
    div[data-testid="stMetric"] {{
        background: linear-gradient(145deg, {CARD_BG}, rgba(15, 23, 42, 0.3)) !important;
        backdrop-filter: blur(12px);
        padding: 24px 20px !important;
        border-radius: 16px;
        border: 1px solid {BORDER};
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    div[data-testid="stMetric"]:hover {{
        transform: translateY(-3px);
        border-color: rgba(139, 92, 246, 0.4);
    }}
    div[data-testid="stMetricValue"] {{
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #f8fafc !important;
    }}
    div[data-testid="stMetricLabel"] {{
        font-size: 0.95rem !important;
        color: #94a3b8 !important;
        font-weight: 500 !important;
        margin-bottom: 8px;
    }}
    .gradient-header {{
        background: -webkit-linear-gradient(45deg, {PRIMARY}, {CYAN});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        margin-bottom: 0;
    }}
    #MainMenu, footer, header {{ visibility: hidden; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 24px; background-color: transparent; }}
    .stTabs [data-baseweb="tab"] {{ height: 50px; background-color: transparent; border-radius: 4px 4px 0 0; }}
    .stTabs [aria-selected="true"] {{ color: {PRIMARY} !important; font-weight: 600; }}
</style>
""", unsafe_allow_html=True)

# =====================================================
# SUPABASE CONNECTION & TIME MATH
# =====================================================
def get_client():
    dotenv_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    else:
        load_dotenv()
    
    # Increase connection timeout to 60s to handle network latency
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
        options=ClientOptions(postgrest_client_timeout=60)
    )

# Establish IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

def get_date_range(option):
    now = datetime.now(IST)
    start = None
    end = None
    
    if option == "Today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif option == "Yesterday":
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=1)
    elif option == "This Month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif option == "This Year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif option == "Last Year":
        start = now.replace(year=now.year-1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(year=now.year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Convert to UTC ISO for Supabase
    start_utc = start.astimezone(timezone.utc).isoformat() if start else None
    end_utc = end.astimezone(timezone.utc).isoformat() if end else None
    return start_utc, end_utc

@st.cache_data(ttl=30)
def fetch_filtered_data(range_label):
    url = "http://localhost:3001/api/dashboard/data"
    start_utc, end_utc = get_date_range(range_label)
    
    # Snapshot path for emergency fallback if backend is down
    snapshot_path = os.path.join(os.path.dirname(__file__), 'backend', 'data_snapshot.json')

    try:
        # 1. Try fetching from Backend Proxy
        params = {"range_label": range_label, "start_utc": start_utc, "end_utc": end_utc}
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        return (
            pd.DataFrame(data.get("leads", [])),
            pd.DataFrame(data.get("deals", [])),
            pd.DataFrame(data.get("metrics", [])),
            pd.DataFrame(data.get("ai_table", [])),
            data.get("source", "live")
        )
    except Exception as e:
        # 2. Fallback to Local Snapshot if backend/network is unreachable
        if os.path.exists(snapshot_path):
            with open(snapshot_path, 'r') as f:
                data = json.load(f)
            return (
                pd.DataFrame(data.get("leads", [])),
                pd.DataFrame(data.get("deals", [])),
                pd.DataFrame(data.get("metrics", [])),
                pd.DataFrame(data.get("ai_table", [])),
                "cache"
            )
        raise ConnectionError(f"Backend unreachable and no local cache found. {str(e)}")

    # Centers the entire dashboard content for better balance on large screens
    st.markdown("""
        <style>
            .block-container {
                max-width: 1200px;
                padding-left: 2rem;
                padding-right: 2rem;
            }
        </style>
    """, unsafe_allow_html=True)

# =====================================================
# HEADER
# =====================================================
# More balanced header columns
c1, c2 = st.columns([10, 2])
c1.markdown("<h2 class='gradient-header' style='margin-bottom:0;'>💠 Aha CRM Intelligence</h2>", unsafe_allow_html=True)

if c2.button("🔄 Sync AI / Cache", width="stretch"):
    refresh()

st.divider()

# -----------------------------------------------------
# TABS & FILTER ROW
# -----------------------------------------------------
# We use columns to put the filter on the same line as the tab headers
# -----------------------------------------------------
# TABS & FILTER ROW
# -----------------------------------------------------
# Tighter column logic to prevent "off-centered" feel
tc1, tc2 = st.columns([10, 2])

with tc2:
    # Adjusting vertical alignment to match the tab labels precisely
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    date_range = st.selectbox(
        "Period Filter",
        ["Today", "Yesterday", "This Month", "This Year", "Last Year", "All Time"],
        index=0,
        label_visibility="collapsed"
    )

with tc1:
    tab_today, tab_pipeline, tab_ai = st.tabs([
        "⚡ Strategic Pulse",
        "📊 Pipeline Performance",
        "🧠 AI Executive Insights"
    ])

# =====================================================
# LOAD & PREP DATA
# =====================================================
try:
    with st.spinner(f"⚡ Fetching {date_range} Pipeline..."):
        leads, deals, metrics, ai_table, data_source = fetch_filtered_data(date_range)
        
        if data_source == "cache":
            st.warning("📡 Offline Mode: Displaying last successful data snapshot (Supabase unreachable).")
        
        # Define Filter Boundaries
        start_utc, end_utc = get_date_range(date_range)
        
        # Convert UTC strings to IST datetimes
        if not leads.empty:
            leads["created_time"] = pd.to_datetime(leads["created_time"], utc=True).dt.tz_convert(IST)
        if not deals.empty:
            deals["created_time"] = pd.to_datetime(deals["created_time"], utc=True).dt.tz_convert(IST)
            deals["modified_time"] = pd.to_datetime(deals["modified_time"], utc=True).dt.tz_convert(IST)
            deals["closed_time"] = pd.to_datetime(deals["closed_time"], utc=True).dt.tz_convert(IST)
            deals["stage"] = deals["stage"].astype(str)
            deals["amount"] = pd.to_numeric(deals["amount"], errors="coerce").fillna(0)

        # Apply Global Filter
        if date_range != "All Time":
            if start_utc:
                st_ts = pd.to_datetime(start_utc, utc=True).tz_convert(IST)
                leads = leads[leads["created_time"] >= st_ts]
                deals = deals[
                    (deals["created_time"] >= st_ts) | 
                    (deals["modified_time"] >= st_ts) |
                    (deals["closed_time"] >= st_ts)
                ]
            if end_utc:
                en_ts = pd.to_datetime(end_utc, utc=True).tz_convert(IST)
                leads = leads[leads["created_time"] < en_ts]
                deals = deals[
                    (deals["created_time"] < en_ts) & 
                    (
                        (deals["modified_time"] < en_ts) |
                        (deals["closed_time"] < en_ts)
                    )
                ]
except ConnectionError as ce:
    st.error(f"❌ Network Error: {str(ce)}")
    st.info("� Tip: Try pinging your Supabase URL or checking if your VPN is blocking the connection.")
    st.stop()
except Exception as e:
    st.error(f"📡 API Error: Supabase is taking too long to respond or returned an error. {str(e)}")
    st.warning("🔄 Please check your internet connection and ensure your Supabase project is active.")
    st.stop()

# Define Tab Objects (Inside tc1 to keep filter on same line)
# Note: Data loading moved UP to before tab rendering

# -----------------------------------------------------
# STRATEGIC PULSE TAB
# -----------------------------------------------------
with tab_today:
    # Use pre-calculated backend metrics only for "Today"
    if date_range == "Today" and not metrics.empty:
        m = metrics.iloc[0]
        def safe_i(v): 
            try: return int(v)
            except: return 0
        def safe_f(v): 
            try: return float(v)
            except: return 0.0

        t_leads   = safe_i(m.get("new_leads_today", len(leads)))
        t_won     = safe_i(m.get("deals_closed", 0))
        rev_won   = safe_f(m.get("deal_amount_won", 0))
        rev_lost  = safe_f(m.get("deal_amount_lost", 0))
        t_rev     = safe_f(m.get("total_revenue", 0))
        win_rate  = (rev_won / (rev_won + rev_lost) * 100) if (rev_won + rev_lost) > 0 else 0
        t_nego    = safe_i(m.get("negotiations_active", 0))
        t_prop    = safe_i(m.get("proposals_sent", 0))
        avg_deal  = (rev_won / t_won) if t_won > 0 else 0
    else:
        # Calculate from already globally-filtered leads/deals
        won_deals = deals[deals["stage"].str.contains("closed won", case=False, na=False)] if not deals.empty else pd.DataFrame()
        lost_deals = deals[deals["stage"].str.contains("closed lost", case=False, na=False)] if not deals.empty else pd.DataFrame()
        
        t_leads   = len(leads)
        t_won     = len(won_deals)
        rev_won   = won_deals["amount"].sum() if not won_deals.empty else 0
        rev_lost  = lost_deals["amount"].sum() if not lost_deals.empty else 0
        t_rev     = deals["amount"].sum() if not deals.empty else 0 # Total Volume touched
        win_rate  = (rev_won / (rev_won + rev_lost) * 100) if (rev_won + rev_lost) > 0 else 0
        t_nego    = len(deals[deals["stage"].str.contains("negotiation", case=False, na=False)]) if not deals.empty else 0
        t_prop    = len(deals[deals["stage"].str.contains("proposal|quote", case=False, na=False)]) if not deals.empty else 0
        avg_deal  = (rev_won / t_won) if t_won > 0 else 0

    st.markdown(f"#### ⚡ {date_range} Performance")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("🆕 New Leads",           human_format(t_leads))
    k2.metric("🤝 Active Negotiations",  human_format(t_nego))
    k3.metric("🏆 Deals Won",           human_format(t_won))
    k4.metric("💰 Revenue Won",         human_format(rev_won, True))
    k5.metric("📉 Revenue Lost",        human_format(rev_lost, True))

    st.divider()

    st.markdown("#### 🏁 Period Outcomes")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("💵 Revenue Touched",      human_format(t_rev, True))
    d2.metric("📊 Period Win Rate",      f"{win_rate:.1f}%")
    d3.metric("📄 Proposals Sent",       human_format(t_prop))
    d4.metric("🎯 Avg Deal Size",        human_format(avg_deal, True))

    st.divider()

    if date_range == "Today" and not metrics.empty:
        m = metrics.iloc[0]
        st.markdown("#### 🗓️ Today's Lifecycle Activity *(from daily sync)*")
        l1, l2, l3, l4, l5 = st.columns(5)
        l1.metric("📞 Contacted",      human_format(safe_i(m.get("leads_contacted", 0))))
        l2.metric("⭐ Qualified",      human_format(safe_i(m.get("qualified_leads", 0))))
        l3.metric("📅 Demo Sched.",    human_format(safe_i(m.get("demos_scheduled", 0))))
        l4.metric("🖥️ Demo Held",      human_format(safe_i(m.get("demos_held", 0))))
        l5.metric("⏱️ Last Synced",    str(m.get("updated_at","—"))[:16].replace("T"," "))


# -----------------------------------------------------
# TODAY's PIPELINE TAB
# -----------------------------------------------------
with tab_pipeline:
    if leads.empty and deals.empty:
        st.info(f"No leads or deals recorded for {date_range}. 🚀")
    else:
        def chart_layout(fig, title=""):
            fig.update_layout(
                title=dict(text=title, font=dict(size=14, color="#e2e8f0"), x=0),
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=8, r=8, t=40, b=8),
                font=dict(family="Inter, sans-serif", color="#94a3b8"),
                yaxis=dict(gridcolor=GRID, zeroline=False),
                xaxis=dict(gridcolor=GRID, zeroline=False),
            )
            return fig

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"#### ⏳ Leads by Hour ({date_range})")
            if not leads.empty:
                # Group by hour to see when leads are coming in
                leads["hour"] = leads["created_time"].dt.hour
                hourly = leads.groupby("hour").size().reset_index(name="Leads")
                
                # Ensure all 24 hours are represented for a clean chart
                all_hours = pd.DataFrame({"hour": range(24)})
                hourly = all_hours.merge(hourly, on="hour", how="left").fillna(0)
                
                fig = px.area(hourly, x="hour", y="Leads", color_discrete_sequence=[PRIMARY])
                fig.update_traces(fill="tozeroy", line=dict(color=PRIMARY, width=3), fillcolor="rgba(139,92,246,0.15)")
                fig.update_xaxes(tickmode='linear', tick0=0, dtick=3, title="Hour of Day (IST)")
                st.plotly_chart(chart_layout(fig), width="stretch")
            else:
                st.info(f"No leads generated during {date_range}.")

        with col2:
            st.markdown(f"#### 🎯 {date_range} Sources")
            if not leads.empty:
                src = leads["source"].value_counts().reset_index()
                src.columns = ["Source", "Count"]
                fig = px.pie(
                    src, values="Count", names="Source", hole=0.65,
                    color_discrete_sequence=[PRIMARY, CYAN, ACCENT, SUCCESS, DANGER, SECONDARY]
                )
                fig.update_traces(textfont_size=12, textinfo='percent', marker=dict(line=dict(color=BG, width=3)))
                fig.update_layout(legend=dict(orientation="h", y=-0.15))
                st.plotly_chart(chart_layout(fig), width="stretch")

        st.divider()

        col3, col4 = st.columns(2)

        with col3:
            st.markdown(f"#### 👥 Team Performance ({date_range})")
            if not deals.empty:
                won_period = deals[deals["stage"].str.contains("closed won", case=False, na=False)]
                t_total = deals.groupby("owner_name").size().reset_index(name="Touched")
                t_won   = won_period.groupby("owner_name").size().reset_index(name="Won") if not won_period.empty else pd.DataFrame(columns=["owner_name", "Won"])
                
                team = t_total.merge(t_won, on="owner_name", how="left").infer_objects(copy=False).fillna(0)
                fig = px.bar(
                    team, x="owner_name", y=["Touched", "Won"],
                    barmode="group",
                    color_discrete_map={"Touched": SECONDARY, "Won": SUCCESS},
                    text_auto='.2s'
                )
                fig.update_layout(legend=dict(orientation="h", y=1.1, x=0, title=""))
                st.plotly_chart(chart_layout(fig), width="stretch")
            else:
                st.info(f"No deal activity assigned for {date_range}.")

        with col4:
            st.markdown(f"#### 💰 {date_range} Pipeline Value")
            if not deals.empty:
                pv = deals.groupby("stage")["amount"].sum().reset_index().sort_values("amount", ascending=True)
                fig = px.bar(
                    pv, x="amount", y="stage", orientation="h",
                    color="amount",
                    color_continuous_scale=[[0, SECONDARY], [0.5, PRIMARY], [1, CYAN]],
                    text=pv["amount"].apply(lambda x: human_format(x, True))
                )
                fig.update_traces(textposition='outside')
                fig.update_coloraxes(showscale=False)
                st.plotly_chart(chart_layout(fig), width="stretch")
            else:
                st.info(f"No deals in the pipeline for {date_range}.")

        st.divider()

        st.markdown(f"#### 📰 {date_range} Deal Activity Log")
        recent = deals.sort_values("created_time", ascending=False).head(20) if not deals.empty else pd.DataFrame()
        if not recent.empty:
            for _, row in recent.iterrows():
                is_won  = "won"  in str(row["stage"]).lower()
                is_lost = "lost" in str(row["stage"]).lower()
                badge_color = SUCCESS if is_won else DANGER if is_lost else ACCENT
                
                # Show full date if not Today
                if date_range == "Today":
                    time_str = row["created_time"].strftime("%I:%M %p")
                else:
                    time_str = row["created_time"].strftime("%b %d, %I:%M %p")
                
                st.markdown(f"""
                <div style="display:flex; align-items:center; justify-content:space-between;
                            background: {CARD_BG}; border:1px solid rgba(255,255,255,0.04);
                            border-radius:12px; padding:16px 20px; margin-bottom:12px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="display:flex; align-items:center; gap:16px;">
                        <div style="width:42px; height:42px; border-radius:12px;
                                    background:{badge_color}22; display:flex;
                                    align-items:center; justify-content:center;
                                    font-size:1.2rem; border: 1px solid {badge_color}44;">
                            {"✅" if is_won else "❌" if is_lost else "🔄"}
                        </div>
                        <div>
                            <p style="margin:0; font-size:0.95rem; font-weight:600; color:#f8fafc;">
                                {row.get("deal_name","Unnamed Deal")}
                            </p>
                            <p style="margin:4px 0 0 0; font-size:0.8rem; color:#94a3b8;">
                                👤 {row.get("owner_name","Unassigned")} &nbsp;·&nbsp; ⏱️ {time_str}
                            </p>
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <p style="margin:0 0 6px 0; font-size:1.05rem; font-weight:700; color:{SUCCESS};">
                            {human_format(row["amount"], True)}
                        </p>
                        <span style="background:{badge_color}15; color:{badge_color};
                                     font-size:0.7rem; font-weight:700; letter-spacing:0.05em;
                                     padding:4px 12px; border-radius:99px; text-transform:uppercase;
                                     border: 1px solid {badge_color}33;">
                            {row["stage"]}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info(f"No deal activity recorded for {date_range}.")


# -----------------------------------------------------
# AI TAB
# -----------------------------------------------------
with tab_ai:
    if not ai_table.empty:
        latest = ai_table.iloc[0]
        payload = latest.get("payload", {})
        summary = payload.get("aiSummary", {}).get("text", "No summary available")

        st.markdown(f"""
        <div style="background: linear-gradient(145deg, {CARD_BG}, rgba(15,23,42,0.8)); 
                    padding: 32px; border-radius: 20px; border: 1px solid {BORDER};
                    box-shadow: 0 10px 30px -10px rgba(0,0,0,0.3);">
            <h3 style="margin-top:0; margin-bottom: 20px;" class="gradient-header">
                ✨ Latest Strategic Briefing
            </h3>
            <div style="line-height: 1.7; font-size: 1.05rem; color: #e2e8f0;">
                {summary}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No AI insights generated yet.")