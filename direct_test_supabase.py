from supabase import create_client
from dotenv import load_dotenv
import os

def test_supabase_connection():
    # Use service_role token from .env file
    load_dotenv()
    
    supabase_url = os.environ.get("SUPABASE_URL") or "https://krjeghqfszngpoogvnrd.supabase.co"
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    if not supabase_key:
        # If no key in .env, use this as fallback
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtyamVnaHFmc3puZ3Bvb2d2bnJkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0MDcwMDY0MSwiZXhwIjoyMDU2Mjc2NjQxfQ.II-HxLnt0Mm_Ql3xkn5EZ0NY-kYlODQ-cS7pSsL6iZg"
    
    try:
        # Initialize Supabase client
        print("Initializing Supabase client...")
        supabase = create_client(supabase_url, supabase_key)
        print(f"Supabase client initialized with URL: {supabase_url}")
        
        # Check all relevant tables
        tables = [
            'inventory_items', 
            'inventory_movements',
            'inventory_categories', 
            'inventory_scans'
        ]
        
        all_tables_exist = True
        print("\nChecking tables:")
        
        for table in tables:
            try:
                print(f"  Checking table '{table}'...")
                response = supabase.table(table).select('count').limit(1).execute()
                print(f"  ✅ '{table}' exists")
            except Exception as e:
                print(f"  ❌ Error accessing '{table}': {str(e)}")
                all_tables_exist = False
        
        if all_tables_exist:
            print("\n✅ All tables exist and are accessible")
        else:
            print("\n⚠️ Some tables could not be accessed")
            
        return True
        
    except Exception as e:
        print(f"❌ Error initializing Supabase client: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing direct Supabase connection...")
    test_supabase_connection() 