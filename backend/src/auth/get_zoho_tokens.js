// Run this script from the terminal: 
// node get_zoho_tokens.js <YOUR_AUTHORIZATION_CODE>

import fetch from 'node-fetch';
import { config } from '../config/env.js';

async function getTokens() {
    // Read code from .env or CLI argument
    const code = process.env.ZOHO_AUTH_CODE || process.argv[2];

    if (!code || code === 'your_zoho_auth_code') {
        console.error("❌ Please provide the authorization code.");
        console.log("Usage: node get_zoho_tokens.js 1000.xxxxxxxxxxxxxx");
        process.exit(1);
    }

    const { clientId, clientSecret } = config.zoho;

    if (!clientId || !clientSecret) {
        console.error("❌ Missing ZOHO_CLIENT_ID or ZOHO_CLIENT_SECRET in .env file.");
        process.exit(1);
    }

    // Note: Zoho requires the exact redirect_uri that you used in your Self Client / OAuth setup
    // to generate the authorization code. If you didn't use one, it's often 'http://localhost' 
    // or your registered callback URL. Update this if necessary.
    const redirectUri = process.env.ZOHO_REDIRECT_URI || 'http://localhost';

    // Depending on your Zoho datacenter, this might be .in, .com, .eu, or .com.au
    const url = `https://accounts.zoho.in/oauth/v2/token?grant_type=authorization_code&client_id=${clientId}&client_secret=${clientSecret}&redirect_uri=${redirectUri}&code=${code}`;

    try {
        console.log("🔄 Exchanging authorization code for tokens...");
        const response = await fetch(url, { method: 'POST' });
        const data = await response.json();

        if (data.error) {
            console.error("\n❌ Error from Zoho:", data);
        } else {
            console.log("\n✅ SUCCESS! Save the refresh_token securely.");
            console.log("-----------------------------------------");
            console.log("Refresh Token :", data.refresh_token);
            console.log("Access Token  :", data.access_token);
            console.log("Expires In (s):", data.expires_in);
            console.log("-----------------------------------------");
            console.log("👉 Next Step: Copy the Refresh Token and paste it as ZOHO_REFRESH_TOKEN in your .env file.");
        }
    } catch (error) {
        console.error("\n❌ Request failed:", error);
    }
}

getTokens();
