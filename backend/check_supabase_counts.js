import { supabase } from './src/utils/supabaseClient.js';
import dotenv from 'dotenv';
dotenv.config();

async function checkCounts() {
    const { count: leadsCount, error: leadsError } = await supabase
        .from('crm_leads')
        .select('*', { count: 'exact', head: true });
    
    const { count: dealsCount, error: dealsError } = await supabase
        .from('crm_deals')
        .select('*', { count: 'exact', head: true });

    console.log('--- Supabase Record Counts ---');
    console.log('Leads:', leadsCount);
    console.log('Deals:', dealsCount);
    if (leadsError) console.error('Leads Error:', leadsError);
    if (dealsError) console.error('Deals Error:', dealsError);
}

checkCounts();
