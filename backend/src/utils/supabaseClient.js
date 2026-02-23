import { createClient } from '@supabase/supabase-js';
import { config } from '../config/env.js';

if (!config.supabase.url || !config.supabase.serviceKey) {
    console.warn("⚠️ WARNING: Supabase credentials not found. Ensure SUPABASE_URL and SUPABASE_SERVICE_KEY are in your .env");
}

export const supabase = createClient(
    config.supabase.url || 'http://localhost:54321', // Fallback to local dev port
    config.supabase.serviceKey || 'mock-service-key',
    {
        auth: {
            persistSession: false,
        }
    }
);
