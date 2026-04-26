
import { createClient } from '@supabase/supabase-js';
import fs from 'fs';
import path from 'path';

// Manually parse .env file
function loadEnv(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');
    for (const line of lines) {
      const [key, value] = line.split('=');
      if (key && value) {
        process.env[key.trim()] = value.trim();
      }
    }
  } catch (err) {
    console.error("Could not read .env file:", err.message);
  }
}

const envPath = path.resolve('e:/website/landing-page-redesign-main/.env');
loadEnv(envPath);

const supabaseUrl = process.env.VITE_SUPABASE_URL;
const supabaseKey = process.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error("Supabase credentials not found in .env");
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function countUsers() {
  console.log("Checking data in Supabase...");
  
  const { count: leadsCount, error: leadsError } = await supabase
    .from('leads')
    .select('*', { count: 'exact', head: true });

  const { count: appCount, error: appError } = await supabase
    .from('work_applications')
    .select('*', { count: 'exact', head: true });

  const { count: queriesCount, error: queriesError } = await supabase
    .from('querries')
    .select('*', { count: 'exact', head: true });

  if (leadsError) console.error("Error fetching leads:", leadsError.message);
  if (appError) console.error("Error fetching applications:", appError.message);
  if (queriesError) console.error("Error fetching queries:", queriesError.message);

  console.log("\n--- Interaction Statistics ---");
  console.log(`Total Leads (Customers): ${leadsCount || 0}`);
  console.log(`Total Work Applications: ${appCount || 0}`);
  console.log(`Total Contact Queries: ${queriesCount || 0}`);
  console.log("------------------------------");
  
  const totalInteractions = (leadsCount || 0) + (appCount || 0) + (queriesCount || 0);
  console.log(`Total engaged users (who filled forms): ${totalInteractions}`);
}

countUsers();
