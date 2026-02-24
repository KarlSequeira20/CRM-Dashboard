-- =====================================================
-- AHA CRM — COMPLETE DATABASE SCHEMA
-- =====================================================

-- ==========================================
-- 1️⃣ CRM LEADS
-- ==========================================
CREATE TABLE IF NOT EXISTS public.crm_leads (
    lead_id TEXT PRIMARY KEY,
    owner_name TEXT NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,

    is_converted BOOLEAN DEFAULT FALSE,

    created_time TIMESTAMPTZ NOT NULL,
    modified_time TIMESTAMPTZ NOT NULL,

    synced_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_created
ON public.crm_leads (created_time DESC);

CREATE INDEX IF NOT EXISTS idx_leads_status
ON public.crm_leads (status);

CREATE INDEX IF NOT EXISTS idx_leads_source
ON public.crm_leads (source);


-- ==========================================
-- 2️⃣ CRM DEALS
-- ==========================================
CREATE TABLE IF NOT EXISTS public.crm_deals (
    deal_id TEXT PRIMARY KEY,

    lead_id TEXT REFERENCES public.crm_leads(lead_id) ON DELETE SET NULL,

    deal_name TEXT NOT NULL,
    owner_name TEXT NOT NULL,
    stage TEXT NOT NULL,
    source TEXT NOT NULL,

    amount NUMERIC(15,2) DEFAULT 0,

    created_time TIMESTAMPTZ NOT NULL,
    modified_time TIMESTAMPTZ NOT NULL,
    closed_time TIMESTAMPTZ,

    synced_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deals_stage
ON public.crm_deals (stage);

CREATE INDEX IF NOT EXISTS idx_deals_closed
ON public.crm_deals (closed_time);

CREATE INDEX IF NOT EXISTS idx_deals_owner
ON public.crm_deals (owner_name);


-- ==========================================
-- 3️⃣ AI SUMMARIES
-- ==========================================
CREATE TABLE IF NOT EXISTS public.ai_summaries (
    id BIGSERIAL PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_created
ON public.ai_summaries (created_at DESC);


-- ==========================================
-- 4️⃣ DAILY METRICS SUMMARY
-- Single Row Snapshot Table
-- ==========================================
CREATE TABLE IF NOT EXISTS public.daily_metrics_summary (
    id INTEGER PRIMARY KEY DEFAULT 1,

    metric_date DATE DEFAULT CURRENT_DATE,

    new_leads_today INTEGER DEFAULT 0,
    leads_contacted INTEGER DEFAULT 0,
    qualified_leads INTEGER DEFAULT 0,
    demos_scheduled INTEGER DEFAULT 0,
    demos_held INTEGER DEFAULT 0,
    proposals_sent INTEGER DEFAULT 0,
    negotiations_active INTEGER DEFAULT 0,

    deals_closed INTEGER DEFAULT 0,

    deal_amount_won NUMERIC(15,2) DEFAULT 0,
    deal_amount_lost NUMERIC(15,2) DEFAULT 0,
    total_revenue NUMERIC(15,2) DEFAULT 0,

    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT single_row CHECK (id = 1)
);

CREATE INDEX IF NOT EXISTS idx_daily_metrics_date
ON public.daily_metrics_summary (metric_date DESC);


-- Insert the required single row if not exists
INSERT INTO public.daily_metrics_summary (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;


-- ==========================================
-- 5️⃣ SYNC STATE (Incremental Cursor Tracking)
-- ==========================================
CREATE TABLE IF NOT EXISTS public.sync_state (
    module_name TEXT PRIMARY KEY,
    last_sync_time TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO public.sync_state (module_name, last_sync_time)
VALUES 
    ('Leads', '2026-01-01T00:00:00Z'),
    ('Deals', '2026-01-01T00:00:00Z')
ON CONFLICT (module_name) DO NOTHING;