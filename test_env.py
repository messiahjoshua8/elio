import os
from dotenv import load_dotenv
import sys

print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f".env file exists: {os.path.exists('.env')}")

try:
    with open('.env', 'r') as f:
        print("\nContents of .env file:")
        contents = f.read()
        print(contents)
        
        # Check for invisible characters or encoding issues
        print("\nBytes representation of .env file:")
        with open('.env', 'rb') as fb:
            bytes_content = fb.read()
            print(bytes_content)
except Exception as e:
    print(f"Error reading .env file: {str(e)}")

print("\nTrying to load environment variables...")
# Try with different dotenv approaches
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("After load_dotenv():")
    print(f"SUPABASE_URL: {os.environ.get('SUPABASE_URL')}")
    print(f"SUPABASE_KEY: {os.environ.get('SUPABASE_KEY')}")
except Exception as e:
    print(f"Error with load_dotenv: {str(e)}")

# Try alternative method
try:
    from dotenv import dotenv_values
    config = dotenv_values(".env")
    print("\nUsing dotenv_values:")
    print(f"SUPABASE_URL from config: {config.get('SUPABASE_URL')}")
    print(f"SUPABASE_KEY from config: {config.get('SUPABASE_KEY')}")
except Exception as e:
    print(f"Error with dotenv_values: {str(e)}")

# Try manual loading
print("\nTrying manual loading:")
try:
    with open('.env', 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, value = line.split('=', 1)
            os.environ[key] = value
            print(f"Manually set {key}={value[:10]}...")
            
    print("\nAfter manual loading:")
    print(f"SUPABASE_URL: {os.environ.get('SUPABASE_URL')}")
    print(f"SUPABASE_KEY: {os.environ.get('SUPABASE_KEY')}")
except Exception as e:
    print(f"Error with manual loading: {str(e)}")

# Hard-code directly as a last resort
print("\nSetting environment variables directly:")
os.environ["SUPABASE_URL"] = "https://krjeghqfszngpoogvnrd.supabase.co"
os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtyamVnaHFmc3puZ3Bvb2d2bnJkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0MDcwMDY0MSwiZXhwIjoyMDU2Mjc2NjQxfQ.II-HxLnt0Mm_Ql3xkn5EZ0NY-kYlODQ-cS7pSsL6iZg"

print("\nAfter direct setting:")
print(f"SUPABASE_URL: {os.environ.get('SUPABASE_URL')}")
print(f"SUPABASE_KEY: {os.environ.get('SUPABASE_KEY')}") 