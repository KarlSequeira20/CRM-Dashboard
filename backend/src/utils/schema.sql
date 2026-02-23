-- 1. Sync State (Incremental Cursor Tracking)
CREATE TABLE IF NOT EXISTS sync_state (
    module_name TEXT PRIMARY KEY,
    last_sync_time TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. CRM Leads (Zoho Leads Data)
CREATE TABLE IF NOT EXISTS crm_leads (
    lead_id TEXT PRIMARY KEY,
    owner_name TEXT NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    created_time TIMESTAMPTZ NOT NULL,
    modified_time TIMESTAMPTZ NOT NULL,
    is_converted BOOLEAN DEFAULT FALSE,
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. CRM Deals (Zoho Deals Data)
CREATE TABLE IF NOT EXISTS crm_deals (
    deal_id TEXT PRIMARY KEY,
    lead_id TEXT REFERENCES crm_leads(lead_id) ON DELETE SET NULL,
    deal_name TEXT NOT NULL,
    owner_name TEXT NOT NULL,
    stage TEXT NOT NULL,
    source TEXT NOT NULL,
    amount NUMERIC(15, 2) DEFAULT 0,
    created_time TIMESTAMPTZ NOT NULL,
    modified_time TIMESTAMPTZ NOT NULL,
    closed_time TIMESTAMPTZ,
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. AI Summaries (Intelligence Briefing History)
CREATE TABLE IF NOT EXISTS ai_summaries (
    id BIGSERIAL PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_leads_modified ON crm_leads(modified_time);
CREATE INDEX IF NOT EXISTS idx_deals_modified ON crm_deals(modified_time);
CREATE INDEX IF NOT EXISTS idx_deals_stage ON crm_deals(stage);
CREATE INDEX IF NOT EXISTS idx_ai_summaries_created ON ai_summaries(created_at);

-- Initial cursors (Optional: Set a baseline date to avoid syncing entire history)
INSERT INTO sync_state (module_name, last_sync_time)
VALUES 
    ('Leads', '2026-02-17T00:00:00Z'),
    ('Deals', '2026-02-17T00:00:00Z')
ON CONFLICT (module_name) DO NOTHING;
