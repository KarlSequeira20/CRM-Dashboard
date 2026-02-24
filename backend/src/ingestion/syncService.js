import { fetchModifiedRecords } from './zohoClient.js';
import { supabase } from '../utils/supabaseClient.js';

export async function getLastSyncTime(moduleName) {
    // Use ISO8601 format but Zoho expects it WITHOUT milliseconds (e.g. 2026-02-21T08:32:12Z or +05:30)
    // The safest format across data centers is strict ISO 8601 truncating ms.
    const date = new Date(Date.now() - 1 * 24 * 60 * 60 * 1000);
    const fallbackTime = date.toISOString().split('.')[0] + 'Z';

    const { data, error } = await supabase
        .from('sync_state')
        .select('last_sync_time')
        .eq('module_name', moduleName)
        .single();

    if (error || !data) {
        return fallbackTime;
    }
    return data.last_sync_time;
}

export async function setLastSyncTime(moduleName, timeString) {
    await supabase
        .from('sync_state')
        .upsert({
            module_name: moduleName,
            last_sync_time: timeString,
            updated_at: new Date().toISOString()
        }, { onConflict: 'module_name' });
}

export async function syncLeads() {
    const lastSync = await getLastSyncTime('Leads');
    const leads = await fetchModifiedRecords('Leads', lastSync);

    if (leads.length === 0) return 0;

    const records = leads.map(l => ({
        lead_id: l.id,
        owner_name: l.Owner?.name || 'Unknown',
        status: l.Lead_Status || 'Unknown',
        source: l.Lead_Source || 'Unknown',
        created_time: l.Created_Time,
        modified_time: l.Modified_Time,
        is_converted: l.Is_Converted || false
    }));

    // De-duplicate records by lead_id to prevent "ON CONFLICT DO UPDATE command cannot affect row a second time"
    const uniqueRecords = Array.from(new Map(records.map(r => [r.lead_id, r])).values());

    const { error } = await supabase.from('crm_leads').upsert(uniqueRecords, { onConflict: 'lead_id' });
    if (error) throw new Error(`Failed to upsert Leads: ${error.message}`);

    const maxModified = [...leads].sort((a, b) => new Date(b.Modified_Time).getTime() - new Date(a.Modified_Time).getTime())[0].Modified_Time;
    await setLastSyncTime('Leads', maxModified);

    return records.length;
}

export async function syncDeals() {
    const lastSync = await getLastSyncTime('Deals');
    const deals = await fetchModifiedRecords('Deals', lastSync);

    if (deals.length === 0) return 0;

    const records = deals.map(d => ({
        deal_id: d.id,
        lead_id: d.Lead_Name?.id || null,
        deal_name: d.Deal_Name,
        owner_name: d.Owner?.name || 'Unknown',
        stage: d.Stage || 'Unknown',
        source: d.Lead_Source || 'Unknown',
        amount: parseFloat(d.Amount || 0),
        created_time: d.Created_Time,
        modified_time: d.Modified_Time,
        closed_time: (d.Stage && d.Stage.includes('Closed')) ? d.Modified_Time : null
    }));

    // De-duplicate records by deal_id to prevent database conflict errors
    const uniqueRecords = Array.from(new Map(records.map(r => [r.deal_id, r])).values());

    const { error } = await supabase.from('crm_deals').upsert(uniqueRecords, { onConflict: 'deal_id' });
    if (error) throw new Error(`Failed to upsert Deals: ${error.message}`);

    const maxModified = [...deals].sort((a, b) => new Date(b.Modified_Time).getTime() - new Date(a.Modified_Time).getTime())[0].Modified_Time;
    await setLastSyncTime('Deals', maxModified);

    return records.length;
}
export async function resetSyncCursors() {
    await supabase.from('sync_state').upsert([
        { module_name: 'Leads', last_sync_time: '2026-02-17T00:00:00Z' },
        { module_name: 'Deals', last_sync_time: '2026-02-17T00:00:00Z' }
    ]);
}
