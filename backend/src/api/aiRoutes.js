import express from 'express';
import { supabase } from '../utils/supabaseClient.js';
import { getFunnelMetrics, getSourceDistribution, getPipelineMetrics } from '../analytics/metrics.js';
import { runPipeline } from '../scheduler/index.js';

const router = express.Router();

router.get('/daily-summary', async (req, res) => {
    try {
        // Fetch the most recent AI summary payload
        const { data, error } = await supabase
            .from('ai_summaries')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(1)
            .single();

        if (error || !data) {
            // If table doesn't exist or is empty, try reading the local fallback file
            const fs = await import('fs');
            const path = await import('path');
            const { fileURLToPath } = await import('url');

            try {
                const __dirname = path.dirname(fileURLToPath(import.meta.url));
                const fallbackPath = path.resolve(__dirname, '../latest_ai_summary.json');

                if (fs.existsSync(fallbackPath)) {
                    const fallbackData = JSON.parse(fs.readFileSync(fallbackPath, 'utf-8'));
                    const stats = fs.statSync(fallbackPath);
                    return res.json({
                        ...fallbackData.aiSummary,
                        overview: fallbackData.overview,
                        vizInsights: fallbackData.vizInsights,
                        lastRunTime: stats.mtime.toISOString()
                    });
                }
            } catch (fsErr) {
                console.error("Local fallback failed:", fsErr);
            }

            return res.status(404).json({ error: "No summaries found yet." });
        }

        if (!data.payload || typeof data.payload !== 'object') {
            console.error("Malformed AI Summary payload in database:", data);
            return res.status(500).json({ error: "Latest summary is malformed." });
        }

        res.json({
            ...(data.payload.aiSummary || {}),
            overview: data.payload.overview || {},
            vizInsights: data.payload.vizInsights || {},
            lastRunTime: data.created_at
        });
    } catch (error) {
        console.error("AI Summary Route Error:", error);
        res.status(500).json({ error: error.message });
    }
});

router.post('/trigger', async (req, res) => {
    try {
        console.log("🚀 Manual Pipeline Triggered from Dashboard");

        // Wait for pipeline to finish for "Real-time" feel
        await runPipeline({ sendWhatsApp: false });

        res.json({ message: "Pipeline completed successfully. Data is now up to date." });
    } catch (error) {
        console.error("Pipeline Trigger Error:", error);
        res.status(500).json({ error: error.message });
    }
});

router.post('/whatsapp/webhook', async (req, res) => {
    try {
        console.log(`[WhatsApp Webhook] Incoming Root Hit:`, req.body);
        const body = req.body.Body || '';
        const from = req.body.From || 'Unknown';

        console.log(`[WhatsApp Webhook] Parsed: "${body}" from ${from}`);

        if (body.trim().toUpperCase() === 'UPDATE') {
            console.log("🚀 WhatsApp Command 'UPDATE' detected. Fetching latest & triggering refresh...");

            // 1. Fetch latest summary to reply immediately
            const { data: latest } = await supabase
                .from('ai_summaries')
                .select('*')
                .order('created_at', { ascending: false })
                .limit(1)
                .single();

            let replyText = "🔄 Syncing Zoho for fresh insights... \n\n";

            if (latest && latest.payload && latest.payload.whatsappSummary) {
                replyText += `*Latest Pulse (${new Date(latest.created_at).toLocaleTimeString()}):*\n${latest.payload.whatsappSummary.text}`;
            } else {
                replyText += "No previous summary found. I'm generating your first one now! 🚀";
            }

            // 2. Trigger fresh pipeline in background
            runPipeline({ sendWhatsApp: true }).catch(err => console.error("WhatsApp 'UPDATE' sync failed:", err));

            res.type('text/xml');
            res.send(`
                <Response>
                    <Message>${replyText}</Message>
                </Response>
            `);
        } else {
            res.type('text/xml');
            res.send(`
                <Response>
                    <Message>Command not recognized. Type "UPDATE" to receive your Revenue Intelligence Brief. 💠</Message>
                </Response>
            `);
        }
    } catch (error) {
        console.error("WhatsApp Webhook Error:", error);
        res.status(500).send("Webhook Error");
    }
});

router.get('/analytics', async (req, res) => {
    try {
        const [funnel, sources, pipeline] = await Promise.all([
            getFunnelMetrics(),
            getSourceDistribution(),
            getPipelineMetrics()
        ]);
        res.json({ funnel, sources: sources.slice(0, 6), pipeline });
    } catch (error) {
        console.error('Analytics Route Error:', error);
        res.status(500).json({ error: error.message });
    }
});

export default router;
