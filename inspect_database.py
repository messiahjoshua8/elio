import os
from supabase import create_client
from dotenv import load_dotenv
import json
import uuid
from datetime import datetime

# Load environment variables
load_dotenv()

def inspect_supabase_database():
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: Supabase credentials not found in environment variables")
        return False
    
    try:
        # Initialize Supabase client
        supabase = create_client(supabase_url, supabase_key)
        print(f"Connected to Supabase project at: {supabase_url}")
        
        # Get a list of all tables
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        """
        
        tables_result = supabase.rpc('execute_sql', {'query': tables_query}).execute()
        
        if not tables_result.data:
            print("No tables found in public schema")
            return
            
        database_schema = {}
        
        # For each table, get its columns and sample data
        for table_info in tables_result.data:
            table_name = table_info['table_name']
            print(f"\nInspecting table: {table_name}")
            
            # Get column information
            columns_query = f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            """
            
            columns_result = supabase.rpc('execute_sql', {'query': columns_query}).execute()
            
            if not columns_result.data:
                print(f"  No columns found for table {table_name}")
                continue
                
            columns = []
            for col in columns_result.data:
                columns.append({
                    'name': col['column_name'],
                    'type': col['data_type'],
                    'nullable': col['is_nullable'] == 'YES'
                })
                print(f"  - {col['column_name']} ({col['data_type']}, {'nullable' if col['is_nullable'] == 'YES' else 'not nullable'})")
            
            # Get a sample record if available
            try:
                sample = supabase.table(table_name).select('*').limit(1).execute()
                sample_data = sample.data[0] if sample.data else None
            except Exception as e:
                print(f"  Error getting sample: {str(e)}")
                sample_data = None
            
            database_schema[table_name] = {
                'columns': columns,
                'sample': sample_data
            }
        
        # Save the schema to a file
        with open('database_schema.json', 'w') as f:
            json.dump(database_schema, f, indent=2)
            
        print("\nDatabase schema saved to database_schema.json")
        return database_schema
        
    except Exception as e:
        print(f"Error inspecting database: {str(e)}")
        return None

def check_compatibility(item_data):
    """Check if our data is compatible with Supabase tables"""
    supabase_url = os.environ.get("SUPABASE_URL") or "https://krjeghqfszngpoogvnrd.supabase.co"
    supabase_key = os.environ.get("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtyamVnaHFmc3puZ3Bvb2d2bnJkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA3MDA2NDEsImV4cCI6MjA1NjI3NjY0MX0.UIbzFoNQ0lF7g-_lyjPt4R2p0HZsKwRD8pp1EoGN050"
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        
        # Check each table for required fields
        tables = ['inventory_scans', 'inventory_items', 'inventory_movements', 'inventory_categories']
        
        for table in tables:
            print(f"\nChecking required fields for table '{table}':")
            columns_query = f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = '{table}'
            AND is_nullable = 'NO'
            AND column_default IS NULL
            """
            
            result = supabase.rpc('execute_sql', {'query': columns_query}).execute()
            
            if result.data:
                print(f"Required fields (not nullable, no default):")
                for col in result.data:
                    print(f"  - {col['column_name']} ({col['data_type']})")
            else:
                print("No required fields found")
                
        # Generate sample data that would work
        print("\nSample data for inventory_scans table:")
        scan_record = {
            'id': str(uuid.uuid4()),
            'created_at': datetime.now().isoformat(),
            'full_text': 'Sample text',
            'product_name': 'Sample Product', 
            'analysis_data': json.dumps({'sample': True})
        }
        print(json.dumps(scan_record, indent=2))
        
    except Exception as e:
        print(f"Error checking compatibility: {str(e)}")

if __name__ == "__main__":
    print("Inspecting Supabase database structure...")
    schema = inspect_supabase_database()
    
    print("\n" + "="*50)
    print("Checking data compatibility...")
    check_compatibility({}) 