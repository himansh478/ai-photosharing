import { createClient } from '@supabase/supabase-js';

const supabaseUrl = 'https://tvqvkunrruqjgtwgjcye.supabase.co';
const supabaseAnonKey = 'sb_publishable_Vxi9_MdnMbxTJE5ekGMaZw_oaRz9qQA';
const supabase = createClient(supabaseUrl, supabaseAnonKey);

async function testBackend() {
  console.log("🚀 STARTING BACKEND TEST...");
  
  const testData = {
    name: "Himansh Test Bot",
    email: "test@cwaya.com",
    whatsapp_number: "+91-9999999999",
    location: "Mumbai",
    service_type: "Insta Auto Reply",
    project_title: "Automated Bot Testing",
    description: "This is an automatic test to verify frontend to backend connection.",
    budget: "₹1000-2500",
    timeline: "ASAP (3-7 days)"
  };

  console.log("📝 1. DUMMY FORM DATA CREATED (Frontend simulation):");
  console.log(testData);
  
  console.log("\n⏳ 2. SENDING TO SUPABASE (https://tvqvkunrruqjgtwgjcye.supabase.co)...");
  const { data, error } = await supabase.from('bookings').insert([testData]).select();

  if (error) {
    console.error("❌ BACKEND ERROR:", error.message);
  } else {
    console.log("✅ 3. SUCCESS! DATA SAVED IN SUPABASE!");
    console.log("⏬ BACKEND RETURNED:");
    console.log(data);
  }
}

testBackend();
