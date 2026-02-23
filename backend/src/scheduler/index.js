import cron from 'node-cron';
import { fileURLToPath } from 'url';
import { syncLeads, syncDeals, resetSyncCursors } from '../ingestion/syncService.js';
import { getDailyMetrics, getSourceDistribution, getFunnelMetrics, getLeadsTrend, getHistoricalAverages, syncDailyMetricsSummary } from '../analytics/metrics.js';
import { generateInsights, generateVizInsights, generateWhatsAppSummary } from '../ai/ollamaClient.js';
import { sendWhatsAppMessage } from '../whatsapp/twilioClient.js';

export async function runPipeline({ sendWhatsApp = false } = {}) {
    console.log(`--- Starting Daily CRM Pipeline (WhatsApp: ${sendWhatsApp}) ---`);

    try {
        console.log('0. Resetting Sync Cursors for Fresh Download...');
        await resetSyncCursors();

        console.log('1. Syncing Fresh Leads...');
        const leadsCount = await syncLeads();
        console.log(`-> Synced ${leadsCount} leads.`);

        console.log('2. Syncing Deals...');
        const dealsCount = await syncDeals();
        console.log(`-> Synced ${dealsCount} deals.`);

        console.log('3. Gathering Analytics...');
        const [metricsPayload, sourceDistribution, funnelMetrics, leadsTrend, historicalAvg] = await Promise.all([
            getDailyMetrics(),
            getSourceDistribution(),
            getFunnelMetrics(),
            getLeadsTrend(),
            getHistoricalAverages(),
            syncDailyMetricsSummary()
        ]);

        // Safe math helper to compute 7-day change accurately
        const calculatePercentChange = (today, avg) => {
            if (avg === 0 || avg === null || avg === undefined || today === undefined) return 0;
            const pct = ((today - avg) / avg) * 100;
            if (isNaN(pct)) return 0;
            return parseFloat(pct.toFixed(1));
        };

        // Map data to precisely match the AI Prompt Schema
        const fullPayload = {
            date: metricsPayload.date || new Date().toISOString(),
            new_leads_today: metricsPayload.metrics.new_leads,
            new_leads_7day_avg: historicalAvg.avgLeads,
            new_leads_change_percent: calculatePercentChange(metricsPayload.metrics.new_leads, historicalAvg.avgLeads),
            leads_trend_30days: leadsTrend,
            leads_by_source: sourceDistribution.map(s => ({ source: s.name, leads: s.value, change_percent: 0 })),
            funnel: {
                leads: funnelMetrics[0]?.count || 0,
                contacted: funnelMetrics.find(f => f.stage === 'Contacted')?.count || 0,
                qualified: funnelMetrics.find(f => f.stage === 'Qualified')?.count || 0,
                proposal_sent: funnelMetrics.find(f => f.stage === 'Proposal Sent')?.count || 0,
                won: funnelMetrics.find(f => f.stage === 'Won')?.count || 0,
                conversion_rate: funnelMetrics[0]?.count > 0 ? ((funnelMetrics[funnelMetrics.length - 1]?.count / funnelMetrics[0]?.count) * 100).toFixed(1) : 0
            },
            pipeline: {
                total_value: metricsPayload.metrics.pipeline_value,
                change_percent: calculatePercentChange(metricsPayload.metrics.pipeline_value, historicalAvg.avgPipeline),
                closed_won_today: metricsPayload.metrics.deals_closed,
                closed_lost_today: 0
            },
            anomaly_flags: metricsPayload.anomalies || []
        };

        console.log('4. Generating AI Insights with Ollama ...');
        const summaryJSON = await generateInsights(fullPayload);

        const vizPayload = { funnel: funnelMetrics, sources: sourceDistribution };
        const vizJSON = await generateVizInsights(vizPayload);

        console.log('4c. Generating Shortened WhatsApp Summary...');
        const whatsappJSON = await generateWhatsAppSummary(fullPayload);

        console.log('5. Saving Structured AI Insights to Database...');
        const { supabase } = await import('../utils/supabaseClient.js');
        const fs = await import('fs');
        const path = await import('path');

        const currentWinRate = parseFloat(fullPayload.funnel.conversion_rate);
        const avgWinRate = 15; // Benchmark

        // Use the returned JSON payload directly 
        const dbPayload = {
            date: metricsPayload.date || new Date().toISOString(),
            overview: {
                newLeads: {
                    value: metricsPayload.metrics.new_leads,
                    changePct: calculatePercentChange(metricsPayload.metrics.new_leads, historicalAvg.avgLeads),
                    trendStr: "vs 7-day avg",
                    isGood: calculatePercentChange(metricsPayload.metrics.new_leads, historicalAvg.avgLeads) >= 0
                },
                conversionRate: {
                    value: `${currentWinRate}%`,
                    changePct: calculatePercentChange(currentWinRate, avgWinRate),
                    trendStr: "vs benchmark",
                    isGood: currentWinRate >= avgWinRate
                },
                dealsClosed: {
                    value: metricsPayload.metrics.deals_closed,
                    changePct: calculatePercentChange(metricsPayload.metrics.deals_closed, historicalAvg.avgDeals),
                    trendStr: "vs 7-day avg",
                    isGood: calculatePercentChange(metricsPayload.metrics.deals_closed, historicalAvg.avgDeals) >= 0
                },
                pipelineValue: {
                    value: `₹${(metricsPayload.metrics.pipeline_value / 100000).toFixed(1)}L`,
                    changePct: calculatePercentChange(metricsPayload.metrics.pipeline_value, historicalAvg.avgPipeline),
                    trendStr: "vs 7-day avg",
                    isGood: calculatePercentChange(metricsPayload.metrics.pipeline_value, historicalAvg.avgPipeline) >= 0
                }
            },
            aiSummary: {
                lastRunTime: new Date().toLocaleString(),
                text: summaryJSON.text || "⚠️ AI analysis was skipped or timed out."
            },
            whatsappSummary: {
                text: whatsappJSON.text || "⚠️ WhatsApp summary not available."
            },
            vizInsights: {
                text: vizJSON.text || "Visualization insight not available."
            }
        };

        const { error: dbError } = await supabase.from('ai_summaries').insert([{ payload: dbPayload }]);
        if (dbError) {
            console.error('[Database] Failed to save AI summary:', dbError.message);
        }

        // Local fallback for Dashboard (if user hasn't created the SQL table)
        try {
            const fallbackPath = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../latest_ai_summary.json');
            fs.writeFileSync(fallbackPath, JSON.stringify(dbPayload, null, 2));
            console.log('[Fallback] Wrote live summary to local disk at:', fallbackPath);
        } catch (fsErr) {
            console.error('[Fallback] Failed to write local cache:', fsErr);
        }

        if (sendWhatsApp) {
            console.log('6. Delivering via WhatsApp...');
            const whatsappText = whatsappJSON.text || "⚠️ AI status update: Successful. Dashboard is refreshed.";
            await sendWhatsAppMessage(whatsappText);
        } else {
            console.log('6. Skipping WhatsApp delivery (sendWhatsApp flag is false).');
        }

        console.log('--- Pipeline Execution Completed Successfully ---');
    } catch (error) {
        console.error('--- Pipeline Execution Failed ---');
        console.error(error);
    }
}

// Check if this module was run directly from the command line
const isMain = process.argv[1] === fileURLToPath(import.meta.url);
if (isMain) {
    runPipeline({ sendWhatsApp: true });
} else {
    // Schedule for 6:00 AM every day when imported as a daemon
    cron.schedule('0 6 * * *', () => {
        console.log('Cron triggered Daily CRM Pipeline...');
        runPipeline({ sendWhatsApp: true });
    });
}
