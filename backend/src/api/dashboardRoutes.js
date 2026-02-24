import express from 'express';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { supabase } from '../utils/supabaseClient.js';

const router = express.Router();
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SNAPSHOT_PATH = path.join(__dirname, '../../../data_snapshot.json');

router.get('/data', async (req, res) => {
    const { range_label, start_utc, end_utc } = req.query;

    try {
        console.log(`[Dashboard Proxy] Fetching data for: ${range_label}`);

        let leads_q = supabase.from('crm_leads').select('lead_id,owner_name,status,source,is_converted,created_time');
        let deals_q = supabase.from('crm_deals').select('deal_id,lead_id,deal_name,owner_name,stage,source,amount,created_time,modified_time,closed_time');

        if (range_label !== 'All Time' && start_utc) {
            leads_q = leads_q.gte('created_time', start_utc);
            if (end_utc) leads_q = leads_q.lt('created_time', end_utc);

            // Inclusive OR filter for deals
            const orFilter = `created_time.gte.${start_utc},modified_time.gte.${start_utc},closed_time.gte.${start_utc}`;
            deals_q = deals_q.or(orFilter);
        }

        const [leadsRes, dealsRes, metricsRes, aiRes] = await Promise.all([
            leads_q,
            deals_q,
            supabase.from('daily_metrics_summary').select('*').limit(1),
            supabase.from('ai_summaries').select('id,payload,created_at').order('created_at', { ascending: false }).limit(1)
        ]);

        if (leadsRes.error) throw leadsRes.error;
        if (dealsRes.error) throw dealsRes.error;

        const payload = {
            leads: leadsRes.data,
            deals: dealsRes.data,
            metrics: metricsRes.data,
            ai_table: aiRes.data,
            timestamp: new Date().toISOString()
        };

        // Cache successful fetch
        fs.writeFileSync(SNAPSHOT_PATH, JSON.stringify(payload, null, 2));
        console.log(`[Dashboard Proxy] Snapshot saved to ${SNAPSHOT_PATH}`);

        res.json({ ...payload, source: 'live' });

    } catch (error) {
        console.error('[Dashboard Proxy] Fetch Error:', error.message);

        // Fallback to cache
        if (fs.existsSync(SNAPSHOT_PATH)) {
            console.log('[Dashboard Proxy] Serving from cache...');
            const cache = JSON.parse(fs.readFileSync(SNAPSHOT_PATH, 'utf-8'));
            return res.json({ ...cache, source: 'cache', error: error.message });
        }

        res.status(502).json({ error: 'Supabase unreachable and no cache found', details: error.message });
    }
});

export default router;
