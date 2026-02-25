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
    englishData += `- Funnel: Leads(${jsonPayload.funnel.leads}) -> Contacted(${jsonPayload.funnel.contacted}) -> Qualified(${jsonPayload.funnel.qualified}) -> Won(${jsonPayload.funnel.won})\n`;
    englishData += `- Current Win Rate: ${jsonPayload.funnel.conversion_rate}%\n`;
  }

  if (jsonPayload.leads_by_source && jsonPayload.leads_by_source.length > 0) {
    const sources = jsonPayload.leads_by_source.map(s => `${s.source}: ${s.leads}`).join(", ");
    englishData += `- Source Distribution: ${sources}\n`;
  }

  const prompt = `
Role: Strict Revenue Analyst.
Objective: Identify the single most significant trend or bottleneck in the data.

DATA TO ANALYZE:
${englishData}

--------------------------------------------------
STRICT OUTPUT FORMAT (START IMMEDIATELY WITH "Primary Driver:"):

Primary Driver:
[Identify the biggest % change or funnel drop-off. Explain it in 2 short sentences.]

Supporting Evidence:
- [Reference the primary metric and its % change]
- [Reference the specific funnel stage or lead source volume]

Contradiction Check:
[State why the other metrics (like Win Rate or Pipeline Value) don't disprove the Primary Driver.]

Operational Impact:
[State exactly how this trend will change the total revenue or sales workload this week.]

Immediate Diagnostic Actions:
- [Action 1: Review the specific source or funnel stage identified above]
- [Action 2: Compare today's conversion rate against the 7-day average]

--------------------------------------------------
RULES:
1. NO PREAMBLE. No "Here is the analysis."
2. DATA ONLY. If a number isn't in the list, do not use it.
3. BE BRUTAL. If leads are down, call it a "Volume Crisis." If conversion is low, call it "Funnel Inefficiency."
4. KEEP IT SHORT. Use bullet points. Maximum 1000 characters.
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
  // Pre-formatting values to save model tokens
  const leadChange = jsonPayload.new_leads_change_percent >= 0 ? `+${jsonPayload.new_leads_change_percent}` : jsonPayload.new_leads_change_percent;
  const pipeValue = (jsonPayload.pipeline.total_value / 100000).toFixed(1);
  const pipeChange = jsonPayload.pipeline.change_percent >= 0 ? `+${jsonPayload.pipeline.change_percent}` : jsonPayload.pipeline.change_percent;

  // Inside your prompt string...
  const prompt = `
Role: Strategic Revenue Intelligence Analyst.

Objective:
Provide a tactical directive for a massive growth day.

STRICT OUTPUT RULES:
- Do NOT use markdown.
- Do NOT use asterisks (*).
- Do NOT use bold or italic formatting.
- Do NOT add extra headings.
- Do NOT add explanations outside the defined format.
- Follow the exact structure below.
- Output plain text only.

DATA:
- Leads: ${jsonPayload.new_leads_today} (+${jsonPayload.new_leads_change_percent}%)
- Pipeline: ₹${pipeValue}L (+${pipeChange}%)
- Conversion: ${jsonPayload.funnel.conversion_rate}%

DIRECTIVE LOGIC:
If Leads AND Pipeline are BOTH surging:
Strategic Solution = Priority Tiering.
Focus Action = Move to tier-based routing.
Execution = Assign high-value pipeline deals to senior reps only.

OUTPUT FORMAT (FOLLOW EXACTLY):

📊 Daily CRM Summary – ${jsonPayload.date}
• New Leads: ${jsonPayload.new_leads_today}
• Deals Won: ${jsonPayload.deals_won_today}
• Pipeline: ₹${pipeValue}L

⚠ Strategic Signal:
– Identify the growth surge clearly in one sentence.

🚀 Tactical Solution:
– Provide the exact tiering execution action in one clear sentence.
`.trim();


  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000); // Shorter timeout for 1B

    const response = await fetch(`${config.ollama.baseUrl}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "llama3.2:1b",
        prompt: prompt,
        stream: false,
        options: {
          temperature: 0.1, // Keep it deterministic
          num_predict: 150
        }
      }),
      signal: controller.signal
    });

    clearTimeout(timeout);
    const data = await response.json();
    return { text: data.response.trim() };
  } catch (error) {
    console.error("[Ollama Client] WhatsApp Summary failed.", error.message);
    return {
      text: `📊 Daily CRM Summary\n• New Leads: ${jsonPayload.new_leads_today}\n• Deals Won: ${jsonPayload.pipeline.closed_won_today}\n• Pipeline: ₹${pipeValue}L\n\n⚠ Signal: Dashboard check required.\n👉 Focus: Manual review of funnel.`
    };
  }
}