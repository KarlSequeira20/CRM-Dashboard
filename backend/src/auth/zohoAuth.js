import { config } from '../config/env.js';
import fetch from 'node-fetch';

let currentAccessToken = null;
let tokenExpiryTime = 0;

export async function getValidAccessToken() {
    // Return cached token if still valid for at least 5 minutes
    if (currentAccessToken && Date.now() < tokenExpiryTime - 5 * 60 * 1000) {
        return currentAccessToken;
    }

    const { refreshToken, clientId, clientSecret } = config.zoho;

    if (!refreshToken || !clientId || !clientSecret) {
        throw new Error('Zoho credentials are not configured.');
    }

    // Using .in as specified in architecture, could be parameterized later
    const url = `https://accounts.zoho.in/oauth/v2/token?refresh_token=${refreshToken}&client_id=${clientId}&client_secret=${clientSecret}&grant_type=refresh_token`;

    try {
        const response = await fetch(url, { method: 'POST' });
        const data = await response.json();

        if (data.error) {
            throw new Error(`Zoho Auth Error: ${data.error}`);
        }

        currentAccessToken = data.access_token;
        tokenExpiryTime = Date.now() + (data.expires_in * 1000); // Usually 3600 seconds

        console.log(`[Zoho Auth] Successfully refreshed token. Expires in ${data.expires_in}s`);
        return currentAccessToken;
    } catch (err) {
        console.error("[Zoho Auth] Failed to refresh token:", err);
        throw err;
    }
}
