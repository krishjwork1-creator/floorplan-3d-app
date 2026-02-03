import { createClient } from '@supabase/supabase-js';

// Go to Supabase -> Settings -> API to find these
const supabaseUrl = 'https://lebfznhghxhddkmealtm.supabase.co'; // e.g., https://xyz.supabase.co
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxlYmZ6bmhnaHhoZGRrbWVhbHRtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MDAyMDI0OSwiZXhwIjoyMDg1NTk2MjQ5fQ.iwdSuFtiHql8zC3aGGmYwpnwEqd6ex31hsYrhtEsaFk';    // The top key (ANON), NOT the service_role key

export const supabase = createClient(supabaseUrl, supabaseKey);