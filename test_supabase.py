import os
from dotenv import load_dotenv
from supabase import create_client
import sys

# Print current working directory
print(f"Current working directory: {os.getcwd()}")

# Check if .env file exists
env_path = os.path.join(os.getcwd(), '.env')
print(f"Checking for .env file at: {env_path}")
print(f"File exists: {os.path.exists(env_path)}")

# Load environment variables with explicit path
load_dotenv(dotenv_path=env_path)

# Print Python version
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

# Hardcode for testing (remove in production)
os.environ["SUPABASE_URL"] = "https://krjeghqfszngpoogvnrd.supabase.co"
os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtyamVnaHFmc3puZ3Bvb2d2bnJkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA3MDA2NDEsImV4cCI6MjA1NjI3NjY0MX0.UIbzFoNQ0lF7g-_lyjPt4R2p0HZsKwRD8pp1EoGN050"

def test_supabase_connection():
    # Get Supabase credentials
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    print(f"SUPABASE_URL: {'Found' if supabase_url else 'Not found'}")
    if supabase_key:
        # Only show first few characters for security
        print(f"SUPABASE_KEY: Found (starts with {supabase_key[:10]}...)")
    else:
        print("SUPABASE_KEY: Not found")
    
    if not supabase_url or not supabase_key:
        print("Error: Supabase credentials not found in environment variables")
        return False
    
    try:
        # Initialize Supabase client
        supabase = create_client(supabase_url, supabase_key)
        print(f"Supabase client initialized with URL: {supabase_url}")
        
        # Check if the inventory table exists by querying it
        try:
            print("Attempting to access the inventory table...")
            response = supabase.table('inventory').select('count').execute()
            print(f"Successfully connected to 'inventory' table")
            print(f"Response data: {response}")
            return True
        except Exception as table_error:
            print(f"Error accessing table: {str(table_error)}")
            print("The 'inventory' table might not exist yet. Let's try to create it...")
            
            # If you want to automatically create the table when it doesn't exist:
            # Note: This requires appropriate permissions
            try:
                # Try to get version to verify general connection
                version = supabase.rpc('version').execute()
                print(f"Successfully connected to Supabase, but 'inventory' table not found.")
                print(f"Database connection works: {version}")
                
                print("\nTo create the inventory table, run the following SQL in your Supabase dashboard:")
                print("""
create table inventory (
  id uuid primary key,
  product_name text,
  brand text,
  type text,
  material text,
  quantity integer,
  is_sterile boolean,
  features text,
  created_at timestamp with time zone,
  full_text text,
  analysis_json jsonb
);
                """)
                return True
            except Exception as e:
                print(f"Error connecting to Supabase: {str(e)}")
                return False
    
    except Exception as e:
        print(f"Error initializing Supabase client: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Supabase connection...")
    result = test_supabase_connection()
    
    if result:
        print("\n✅ Supabase connection test completed")
    else:
        print("\n❌ Supabase connection test failed") 