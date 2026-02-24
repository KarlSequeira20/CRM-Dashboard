import { supabase } from '../utils/supabaseClient.js';

export async function getDailyMetrics() {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const todayIso = today.toISOString();
    const tomorrowIso = tomorrow.toISOString();

    // 1. Today's Live Leads
    const { count: newLeadsCount, error: err1 } = await supabase
        .from('crm_leads')
        .select('*', { count: 'exact', head: true })
        .gte('created_time', todayIso)
        .lt('created_time', tomorrowIso);

    if (err1) throw err1;

    // 2. Deals Closed Today
    const { data: closedDeals, error: err2 } = await supabase
        .from('crm_deals')
        .select('amount')
        .in('stage', ['Closed Won', 'Closed'])
        .gte('closed_time', todayIso)
        .lt('closed_time', tomorrowIso);

    if (err2) throw err2;

    const dealsClosedCount = closedDeals.length;
    const revenueClosed = closedDeals.reduce((sum, d) => sum + (Number(d.amount) || 0), 0);

    // 3. Pipeline Value (Active Deals)
    const { data: activeDeals, error: err3 } = await supabase
        .from('crm_deals')
        .select('amount')
        .not('stage', 'in', '("Closed Won","Closed Lost")');

    if (err3) throw err3;

    const pipelineValue = activeDeals.reduce((sum, d) => sum + (Number(d.amount) || 0), 0);

    // 4. Anomalies / Focus Areas logic
    const anomalies = [];
    const focusAreas = [];

    if (dealsClosedCount === 0) {
        anomalies.push("No deals closed today yet.");
    }

    if (pipelineValue > 100000) {
        focusAreas.push(`Pipeline value is healthy at ₹${pipelineValue}. Focus on closing high-value active deals.`);
    }

    return {
        date: today.toISOString().split('T')[0],
        metrics: {
            new_leads: newLeadsCount || 0,
            deals_closed: dealsClosedCount,
            revenue_closed: revenueClosed,
            pipeline_value: pipelineValue
        },
        anomalies,
        focus_areas: focusAreas
    };
}


export async function getSourceDistribution() {
    const { data: leads, error } = await supabase
        .from('crm_leads')
        .select('source');

    if (error) {
        console.error("Error fetching source distribution:", error);
        return [];
    }

    const counts = {};
    leads.forEach(l => {
        let source = typeof l.source === 'string' ? l.source.trim() : 'Unknown';
        // Clean technical formatting
        const cleanSource = source.replace(/_/g, ' ');
        counts[cleanSource] = (counts[cleanSource] || 0) + 1;
    });

    return Object.keys(counts)
        .map(name => ({ name, value: counts[name] }))
        .sort((a, b) => b.value - a.value);
}

export async function getFunnelMetrics() {
    // 1. Total Leads
    const { count: totalLeads, error: e1 } = await supabase
        .from('crm_leads')
        .select('*', { count: 'exact', head: true });

    // 2. Converted Leads
    const { count: convertedLeads, error: e1b } = await supabase
        .from('crm_leads')
        .select('*', { count: 'exact', head: true })
        .eq('is_converted', true);

    // 3. All Deals to aggregate stages
    const { data: deals, error: e2 } = await supabase
        .from('crm_deals')
        .select('stage');

    if (e1 || e1b || e2) {
        console.error('[Analytics] Error in getFunnelMetrics:', e1 || e1b || e2);
        return [];
    }

    let contacted = 0;
    let qualified = 0;
    let demoScheduled = 0;
    let demoDone = 0;
    let proposalSent = 0;
    let negotiation = 0;
    let won = 0;

    deals.forEach(d => {
        const stage = typeof d.stage === 'string' ? d.stage.trim() : '';
        const lowerStage = stage.toLowerCase();

        // 1. Any deal count as "Contacted" (since a deal exists)
        contacted++;

        // 2. Map specific audited stages
        if (lowerStage === 'awaiting electric plan') {
            qualified++;
        } else if (lowerStage === 'walkthrough completed') {
            demoDone++;
        } else if (lowerStage === 'proposal shared') {
            proposalSent++;
        } else if (lowerStage === 'negotiation/review' || lowerStage === 'closed and advance pending') {
            negotiation++;
        } else if (lowerStage === 'closed won') {
            won++;
        }
        // Fallbacks for fuzzy matching (to catch anything else)
        else if (lowerStage.includes('demo')) demoDone++;
        else if (lowerStage.includes('proposal')) proposalSent++;
        else if (lowerStage.includes('negotiat')) negotiation++;
    });

    // Cumulative logic: each stage includes everyone who passed through it
    const cumulativeWon = won;
    const cumulativeNegotiation = negotiation + cumulativeWon;
    const cumulativeProposal = proposalSent + cumulativeNegotiation;
    const cumulativeDemoDone = demoDone + cumulativeProposal;
    const cumulativeDemoSched = demoScheduled + cumulativeDemoDone; // Note: "Scheduled" wasn't explicitly in the audit top stages
    const cumulativeQualified = qualified + cumulativeDemoSched;
    const cumulativeContacted = contacted; // Contacted is the top level for deals

    const leakFunnel = [
        { stage: "Total Leads", count: totalLeads || 0, color: "#6366f1" },
        { stage: "Converted Leads", count: convertedLeads || 0, color: "#8b5cf6" },
        { stage: "Active Deals", count: contacted, color: "#0ea5e9" },
        { stage: "Won", count: cumulativeWon, color: "#f59e0b" }
    ];

    return {
        fullFunnel: [
            { stage: "New Leads", count: totalLeads || 0, color: "#6366f1" },
            { stage: "Contacted", count: cumulativeContacted, color: "#0ea5e9" },
            { stage: "Qualified", count: Math.max(cumulativeQualified, cumulativeDemoSched), color: "#06b6d4" },
            { stage: "Demo Scheduled", count: cumulativeDemoSched, color: "#14b8a6" },
            { stage: "Demo Done", count: cumulativeDemoDone, color: "#10b981" },
            { stage: "Proposal Sent", count: cumulativeProposal, color: "#22c55e" },
            { stage: "Negotiation", count: cumulativeNegotiation, color: "#84cc16" },
            { stage: "Won", count: cumulativeWon, color: "#f59e0b" }
        ],
        leakFunnel: leakFunnel
    };
}

export async function getPipelineMetrics() {
    const { data: deals, error } = await supabase
        .from('crm_deals')
        .select('stage, amount');

    if (error) {
        console.error("Error fetching pipeline metrics:", error);
        return { stages: [], totalValue: 0 };
    }

    const STAGE_ORDER = ['Qualification', 'Proposal', 'Negotiation', 'Won', 'Lost'];
    const STAGE_COLORS = {
        'Qualification': '#3b82f6',
        'Proposal': '#8b5cf6',
        'Negotiation': '#f59e0b',
        'Won': '#10b981',
        'Lost': '#ef4444'
    };

    const counts = {
        'Qualification': 0,
        'Proposal': 0,
        'Negotiation': 0,
        'Won': 0,
        'Lost': 0
    };

    let totalActiveValue = 0;

    deals.forEach(d => {
        const stage = typeof d.stage === 'string' ? d.stage.trim() : 'Unknown';
        const lowerStage = stage.toLowerCase();
        const amount = Number(d.amount) || 0;

        let mappedStage = null;
        if (lowerStage === 'awaiting electric plan') mappedStage = 'Qualification';
        else if (lowerStage === 'proposal shared') mappedStage = 'Proposal';
        else if (lowerStage === 'negotiation/review' || lowerStage === 'closed and advance pending') mappedStage = 'Negotiation';
        else if (lowerStage === 'closed won') mappedStage = 'Won';
        else if (lowerStage === 'closed lost') mappedStage = 'Lost';

        // Fuzzy fallback for other stages
        else if (lowerStage.includes('qualif')) mappedStage = 'Qualification';
        else if (lowerStage.includes('proposal') || lowerStage.includes('quote')) mappedStage = 'Proposal';
        else if (lowerStage.includes('negotiat')) mappedStage = 'Negotiation';

        if (mappedStage) {
            counts[mappedStage] += amount;
            if (mappedStage !== 'Won' && mappedStage !== 'Lost') {
                totalActiveValue += amount;
            }
        }
    });

    const stagesData = STAGE_ORDER.map(name => ({
        name,
        value: counts[name],
        color: STAGE_COLORS[name]
    }));

    return {
        stages: stagesData,
        totalValue: totalActiveValue
    };
}

export async function getHistoricalAverages() {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(today.getDate() - 7);

    const sevenDaysAgoIso = sevenDaysAgo.toISOString();

    // 1. Avg Leads
    const { data: leads, error: e1 } = await supabase
        .from('crm_leads')
        .select('id')
        .gte('created_time', sevenDaysAgoIso);

    // 2. Avg Deals / Revenue
    const { data: deals, error: e2 } = await supabase
        .from('crm_deals')
        .select('amount, stage')
        .gte('created_time', sevenDaysAgoIso);

    if (e1 || e2) {
        return { avgLeads: 10, avgDeals: 1, avgPipeline: 5000000 }; // safety fallbacks
    }

    const avgLeads = leads.length / 7;
    const avgDeals = deals.length / 7;
    const avgPipeline = deals.reduce((sum, d) => sum + (Number(d.amount) || 0), 0) / 7;

    return {
        avgLeads: parseFloat(avgLeads.toFixed(1)),
        avgDeals: parseFloat(avgDeals.toFixed(1)),
        avgPipeline: parseFloat(avgPipeline.toFixed(0))
    };
}

export async function getLeadsTrend() {
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);

    const { data: leads, error } = await supabase
        .from('crm_leads')
        .select('created_time')
        .gte('created_time', thirtyDaysAgo.toISOString());

    if (error || !leads) return [];

    const trend = {};
    leads.forEach(l => {
        const date = l.created_time ? l.created_time.split('T')[0] : null;
        if (date) trend[date] = (trend[date] || 0) + 1;
    });

    const result = [];
    for (let i = 29; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const iso = d.toISOString().split('T')[0];
        result.push({ date: iso, leads: trend[iso] || 0 });
    }
    return result;
}

export async function syncDailyMetricsSummary() {
    console.log('[Analytics] Synchronizing daily_metrics_summary table...');

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const todayIso = today.toISOString();
    const tomorrowIso = tomorrow.toISOString();

    // 1. New Leads Today
    const { count: newLeadsToday, error: e1 } = await supabase
        .from('crm_leads')
        .select('*', { count: 'exact', head: true })
        .gte('created_time', todayIso)
        .lt('created_time', tomorrowIso);

    // 2. All Leads for status checks
    const { data: allLeads, error: e2 } = await supabase
        .from('crm_leads')
        .select('status');

    // 3. All Deals for stage and revenue checks
    const { data: allDeals, error: e3 } = await supabase
        .from('crm_deals')
        .select('stage, amount, closed_time');

    if (e1 || e2 || e3) {
        console.error('[Analytics] Error fetching data for summary sync:', e1 || e2 || e3);
        return;
    }

    // Calculation logic matching user's dashboard requirements
    const leadsContacted = allLeads.filter(l => (l.status || '').toLowerCase().includes('contact')).length;
    const qualifiedLeads = allLeads.filter(l => (l.status || '').toLowerCase().includes('qualif')).length;

    const demosScheduled = allDeals.filter(d => (d.stage || '').toLowerCase().includes('demo scheduled')).length;
    const demosHeld = allDeals.filter(d => (d.stage || '').toLowerCase().includes('demo held')).length;
    const proposalsSent = allDeals.filter(d => (d.stage || '').toLowerCase().includes('proposal')).length;
    const negotiationsActive = allDeals.filter(d => (d.stage || '').toLowerCase().includes('negotiation')).length;
    // Today-only metrics (using closed_time)
    const dealsClosedToday = allDeals.filter(d => {
        const isWon = (d.stage || '').toLowerCase().includes('closed won');
        if (!isWon || !d.closed_time) return false;
        return d.closed_time >= todayIso && d.closed_time < tomorrowIso;
    }).length;

    const dealAmountWonToday = allDeals
        .filter(d => {
            const isWon = (d.stage || '').toLowerCase().includes('closed won');
            if (!isWon || !d.closed_time) return false;
            return d.closed_time >= todayIso && d.closed_time < tomorrowIso;
        })
        .reduce((sum, d) => sum + (Number(d.amount) || 0), 0);

    const dealAmountLost = allDeals
        .filter(d => (d.stage || '').toLowerCase().includes('closed lost'))
        .reduce((sum, d) => sum + (Number(d.amount) || 0), 0);

    const metricsPayload = {
        new_leads_today: newLeadsToday || 0,
        leads_contacted: leadsContacted,
        qualified_leads: qualifiedLeads,
        demos_scheduled: demosScheduled,
        demos_held: demosHeld,
        proposals_sent: proposalsSent,
        negotiations_active: negotiationsActive,
        deals_closed: dealsClosedToday,
        deal_amount_won: dealAmountWonToday,
        deal_amount_lost: dealAmountLost,
        total_revenue: dealAmountWonToday // Matching today pulse
    };

    // Strategies for table without primary key:
    // We'll wipe the table and insert a single fresh record to ensure iloc[0] works correctly.
    try {
        await supabase.from('daily_metrics_summary').delete().neq('new_leads_today', -1);
        const { error: insertError } = await supabase.from('daily_metrics_summary').insert([metricsPayload]);

        if (insertError) throw insertError;
        console.log('[Analytics] daily_metrics_summary synchronized successfully.');
    } catch (err) {
        console.error('[Analytics] Failed to sync daily_metrics_summary:', err.message);
    }
}
