import fetch from 'node-fetch';
import { getValidAccessToken } from '../auth/zohoAuth.js';

const ZOHO_API_DOMAIN = 'https://www.zohoapis.in/crm/v3';

async function fetchFromZoho(endpoint, method = 'GET', body = null) {
    const accessToken = await getValidAccessToken();
    const url = `${ZOHO_API_DOMAIN}${endpoint}`;

    const options = {
        method,
        headers: {
            'Authorization': `Zoho-oauthtoken ${accessToken}`,
            'Content-Type': 'application/json'
        }
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);

    if (response.status === 204) {
        return { data: [] }; // No Content
    }

    const data = await response.json();
    if (response.status >= 400) {
        throw new Error(`Zoho API Error (${response.status}): ${JSON.stringify(data)}`);
    }

    return data;
}

export async function fetchModifiedRecords(moduleName, lastModifiedTime) {
    console.log(`[Zoho] Fetching ${moduleName} modified since ${lastModifiedTime}`);
    let allRecords = [];
    let page = 1;
    let hasMore = true;

    const criteria = `(Modified_Time:greater_equal:${lastModifiedTime})`;

    while (hasMore) {
        const endpoint = `/${moduleName}/search?criteria=${encodeURIComponent(criteria)}&page=${page}&per_page=200`;
        const response = await fetchFromZoho(endpoint);

        if (response.data && response.data.length > 0) {
            allRecords = allRecords.concat(response.data);
            page++;
            hasMore = response.info && response.info.more_records;
        } else {
            hasMore = false;
        }
    }

    console.log(`[Zoho] Fetched ${allRecords.length} updated ${moduleName}`);
    return allRecords;
}
