import fetch from 'node-fetch';
import { config } from '../config/env.js';

const PROMPT_TEMPLATE = `
You are a strict Revenue Intelligence Analyst.

You will receive a summary of today's tracking metrics.
Your ONLY job is to identify the single biggest issue from the provided data and explain it.
DO NOT invent data. DO NOT mention things not in the text (e.g. social media, marketing campaigns).

--------------------------------------------------
STRICT OUTPUT FORMAT
--------------------------------------------------
YOU MUST START YOUR RESPONSE EXACTLY WITH "Primary Driver:". 
DO NOT output conversational filler.
BASE YOUR ENTIRE ANALYSIS ONLY ON THE NUMBERS IN THE "DATA TO ANALYZE" SECTION BELOW. 
IF A METRIC IS NOT LISTED, IT DOES NOT EXIST. DO NOT HALLUCINATE EXTERNAL CAUSES.

Primary Driver:
[2-3 clear, informative sentences explaining the main issue.]

Supporting Evidence:
- [Fact 1 strictly from the provided data]
- [Fact 2 strictly from the provided data]

Contradiction Check:
[1-2 sentences explaining why other metrics do not contradict this driver.]

Operational Impact:
[2-3 clear, informative sentences on how this affects the business.]

Immediate Diagnostic Actions:
- [Action 1: A highly specific, data-driven next step to address the primary driver (e.g., investigating a specific stage, source, or team).]
- [Action 2: Another concrete, actionable step based on the provided metrics.]

--------------------------------------------------

DATA TO ANALYZE:
{english_data}
`;

export async function generateInsights(jsonPayload) {
  // Pre-process rich payload into simple English for the 1B model
  let englishData = `DATE: ${jsonPayload.date}\n`;

  if (jsonPayload.new_leads_today !== undefined) {
    englishData += `- New Leads Today: ${jsonPayload.new_leads_today} (${jsonPayload.new_leads_change_percent}% vs 7-day avg)\n`;
  }

  if (jsonPayload.pipeline) {
    const val = (jsonPayload.pipeline.total_value / 100000).toFixed(1);
    englishData += `- Total Pipeline Value: ₹${val}L (${jsonPayload.pipeline.change_percent}% vs 7-day avg)\n`;
    englishData += `- Deals Won Today: ${jsonPayload.pipeline.closed_won_today}\n`;
  }

  if (jsonPayload.funnel) {
    englishData += `- Conversion Path: Total Leads(${jsonPayload.funnel.leads}) -> Converted(${jsonPayload.funnel.converted}) -> Active Deals(${jsonPayload.funnel.active_deals}) -> Won(${jsonPayload.funnel.won})\n`;
    englishData += `- Lead-to-Deal Conversion: ${((jsonPayload.funnel.active_deals / jsonPayload.funnel.leads) * 100).toFixed(1)}%\n`;
    englishData += `- Deal Win Rate: ${jsonPayload.funnel.conversion_rate}%\n`;
  }

  if (jsonPayload.leads_by_source && jsonPayload.leads_by_source.length > 0) {
    const sources = jsonPayload.leads_by_source.map(s => `${s.source}: ${s.leads}`).join(", ");
    englishData += `- Source Distribution: ${sources}\n`;
  }

  const prompt = `
Role: Strict Revenue Intelligence Analyst.
Objective: Analyze the CRM metrics below to identify the "Operational Leak" (where the pipeline is stalling).

DATA TO ANALYZE:
${englishData}

--------------------------------------------------
STRICT OUTPUT FORMAT:
You MUST provide the following 5 sections. Be detailed but data-anchored.

Primary Driver:
[2-3 clear, informative sentences explaining the SINGLE BIGGEST LEAK or issue in the sales process.]

Supporting Evidence:
- [Fact 1 about the biggest drop-off/leak with specific numbers]
- [Fact 2 about conversion stall or pipeline health]

Contradiction Check:
[1-2 sentences explaining why other metrics do not contradict this leak identified.]

Operational Impact:
[2-3 clear sentences on how this leak directly affects bottom-line revenue or future growth.]

Immediate Diagnostic Actions:
- [Diagnostic Step 1: Specific action to fix the identified leak]
- [Diagnostic Step 2: Specific action to improve top-of-funnel or closing speed]

RULES:
1. IDENTIFY THE LEAK. Proactively call out if the stall is between Status->Deal or Stage->Won.
2. NO FILLER. Start immediately with "Primary Driver:".
3. ANCHOR TO DATA. Use the specific percentages and values from the metrics.
4. MAX 1500 CHARACTERS.
`.trim();

  // Force Ollama to return JSON (works with llama3.2+ when format="json" is passed)
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => {
      controller.abort();
    }, 90000); // 90 second timeout for detailed generation

    const response = await fetch(`${config.ollama.baseUrl}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "llama3.2:1b",
        prompt: prompt,
        stream: false,
        options: {
          temperature: 0.1,
          num_predict: 480
        }
      }),
      signal: controller.signal
    });

    clearTimeout(timeout);

    if (!response.ok) {
      throw new Error(`Ollama API returned status: ${response.status}`);
    }

    const data = await response.json();
    const rawResponse = data.response.trim();

    return { text: rawResponse };
  } catch (error) {
    console.error("[Ollama Client] Inference failed. Using fallback.", error.message);

    return {
      text: `📊 Daily CRM Summary – Fallback\n\n⚠️ AI analysis was skipped or timed out. Please refer to raw dashboard numbers.\n\nEnsure local Ollama service is running optimally.`
    };
  }
}

const VIZ_PROMPT_TEMPLATE = `
You are a Data Visualization Analyst.
Review the provided Funnel and Source Distribution metrics.
Provide a 2-sentence summary highlighting the largest drop-off in the funnel and the top performing lead source.
No filler. No preamble. Strictly data-driven.

DATA TO ANALYZE:
{json_payload}
`;

export async function generateVizInsights(vizPayload) {
  const prompt = VIZ_PROMPT_TEMPLATE.replace("{json_payload}", JSON.stringify(vizPayload));

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);

    const response = await fetch(`${config.ollama.baseUrl}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "llama3.2:1b",
        prompt: prompt,
        stream: false,
        options: {
          temperature: 0.1,
          num_predict: 150
        }
      }),
      signal: controller.signal
    });

    clearTimeout(timeout);

    if (!response.ok) {
      throw new Error(`Ollama API returned status: ${response.status}`);
    }

    const data = await response.json();
    return { text: data.response.trim() };
  } catch (error) {
    console.error("[Ollama Client] Viz Inference failed.", error.message);
    return {
      text: "Funnel drop-off and top sources currently under evaluation."
    };
  }
}

export async function generateWhatsAppSummary(jsonPayload) {
  const prompt = `
Role: Strict Revenue Intelligence Analyst.
Objective: Summarize the daily CRM metrics into a structured 3-point WhatsApp briefing.

--------------------------------------------------
STRICT OUTPUT FORMAT EXAMPLE:
📊 Daily CRM Summary – [Month Day]
• New Leads: [Number] ([Change]% vs avg)
• Deals Won: [Number]
• Pipeline: [Value]

⚠ Signals:
– [Specific anomaly 1 from data]
– [Specific anomaly 2 from data]

👉 Focus:
– [Specific action 1 based on data]
– [Specific action 2 based on data]
--------------------------------------------------

RULES:
1. NO FILLER. START IMMEDIATELY with the chart emoji.
2. ANCHOR TO DATA. Use the specific percentages and values provided.
3. MAX 400 CHARACTERS. Keep it concise for mobile reading.

DATA:
- Date: ${jsonPayload.date}
- New Leads Today: ${jsonPayload.new_leads_today} (${jsonPayload.new_leads_change_percent}% vs 7-day avg)
- Deals Won Today: ${jsonPayload.pipeline.closed_won_today}
- Pipeline Value: ₹${(jsonPayload.pipeline.total_value / 100000).toFixed(1)}L (${jsonPayload.pipeline.change_percent}% vs avg)
- Funnel: Leads(${jsonPayload.funnel.leads}) -> Won(${jsonPayload.funnel.won})
- Conv Rate: ${jsonPayload.funnel.conversion_rate}%
- Anomalies: ${JSON.stringify(jsonPayload.anomaly_flags)}
`.trim();

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);

    const response = await fetch(`${config.ollama.baseUrl}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "llama3.2:1b",
        prompt: prompt,
        stream: false,
        options: {
          temperature: 0.1,
          num_predict: 200
        }
      }),
      signal: controller.signal
    });

    clearTimeout(timeout);
    const data = await response.json();
    return { text: data.response.trim() };
  } catch (error) {
    console.error("[Ollama Client] WhatsApp Summary failed.", error.message);
    const val = (jsonPayload.pipeline.total_value / 100000).toFixed(1);
    return {
      text: `� Daily CRM Summary\n• New Leads: ${jsonPayload.new_leads_today}\n• Deals Won: ${jsonPayload.pipeline.closed_won_today}\n• Pipeline: ₹${val}L\n\nCheck dashboard for full strategic briefing! 💠`
    };
  }
}
