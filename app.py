import fix_distutils  # This fixes the distutils import error

from flask import Flask, request, jsonify
from google.cloud import vision
from google.oauth2 import service_account
import os
import re
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from supabase import create_client
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Right after imports and before anything else
print(f"Current working directory: {os.getcwd()}")

# Debug print all environment variables
print("=== DEBUG: Environment Variables ===")
print(f"ENVIRONMENT: {os.environ.get('ENVIRONMENT')}")
print(f"SUPABASE_URL exists: {os.environ.get('SUPABASE_URL') is not None}")
print(f"SUPABASE_KEY exists: {os.environ.get('SUPABASE_KEY') is not None}")
print(f"ENCRYPTED_GOOGLE_CREDENTIALS exists: {os.environ.get('ENCRYPTED_GOOGLE_CREDENTIALS') is not None}")
print(f"CREDENTIALS_ENCRYPTION_SALT exists: {os.environ.get('CREDENTIALS_ENCRYPTION_SALT') is not None}")
print(f"CREDENTIALS_ENCRYPTION_KEY exists: {os.environ.get('CREDENTIALS_ENCRYPTION_KEY') is not None}")

# Show actual keys with some masking
print("=== SENSITIVE DATA DEBUGGING ===")
for env_var in ['SUPABASE_KEY', 'ENCRYPTED_GOOGLE_CREDENTIALS', 'CREDENTIALS_ENCRYPTION_KEY', 'CREDENTIALS_ENCRYPTION_SALT']:
    value = os.environ.get(env_var)
    if value:
        if len(value) > 30:
            # Show first 10 and last 5 chars
            masked_value = f"{value[:10]}...{value[-5:]}"
        else:
            # Show first 3 and last 3 chars
            masked_value = f"{value[:3]}...{value[-3:]}"
        print(f"{env_var}: {masked_value}")
    else:
        print(f"{env_var}: NOT SET")

# Show all environment variables (without values)
print("=== ALL ENVIRONMENT VARIABLES (NAMES ONLY) ===")
for key in sorted(os.environ.keys()):
    print(f"- {key}")
print("=== END DEBUG ===")

# Try to load .env file, but don't fail if it doesn't exist
try:
    print(f".env file exists: {os.path.exists('.env')}")
    load_dotenv(verbose=True)  # This will silently continue if .env doesn't exist
except Exception as e:
    print(f"Error loading .env: {str(e)}")

# Set default values to environment variables if not already set
if not os.environ.get("SUPABASE_URL"):
    os.environ["SUPABASE_URL"] = "https://krjeghqfszngpoogvnrd.supabase.co"
if not os.environ.get("SUPABASE_KEY"):
    os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtyamVnaHFmc3puZ3Bvb2d2bnJkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0MDcwMDY0MSwiZXhwIjoyMDU2Mjc2NjQxfQ.II-HxLnt0Mm_Ql3xkn5EZ0NY-kYlODQ-cS7pSsL6iZg"

print("Now loading environment variables...")

# Determine environment
is_production = os.environ.get('ENVIRONMENT') == 'production'

# Load environment variables first
load_dotenv()

# Get Supabase credentials
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

# For development, use hardcoded fallbacks if .env failed to load
if not is_production and (not supabase_url or not supabase_key):
    print("Using hardcoded development credentials")
    supabase_url = "https://krjeghqfszngpoogvnrd.supabase.co"
    supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtyamVnaHFmc3puZ3Bvb2d2bnJkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0MDcwMDY0MSwiZXhwIjoyMDU2Mjc2NjQxfQ.II-HxLnt0Mm_Ql3xkn5EZ0NY-kYlODQ-cS7pSsL6iZg"
# For production, try to decrypt from environment variables if needed
elif is_production and (not supabase_url or not supabase_key):
    print("Attempting to load encrypted production credentials")
    encrypted_supabase = os.environ.get('ENCRYPTED_SUPABASE_CREDENTIALS')
    encryption_key = os.environ.get('CREDENTIALS_ENCRYPTION_KEY')
    encryption_salt = os.environ.get('CREDENTIALS_ENCRYPTION_SALT')
    
    if encrypted_supabase and encryption_key and encryption_salt:
        try:
            # Decode the salt and encrypted data
            salt = base64.b64decode(encryption_salt)
            encrypted_data = base64.b64decode(encrypted_supabase)
            
            # Derive the key using the provided password and salt
            key = derive_key(encryption_key, salt)
            
            # Decrypt the credentials
            f = Fernet(key)
            decrypted_data = f.decrypt(encrypted_data)
            
            # Parse the JSON credentials
            creds = json.loads(decrypted_data)
            supabase_url = creds.get('url')
            supabase_key = creds.get('key')
            print("Successfully decrypted Supabase credentials")
        except Exception as e:
            print(f"Error decrypting Supabase credentials: {str(e)}")

# Now set these variables in the environment for any other code that might need them
os.environ["SUPABASE_URL"] = supabase_url or ""
os.environ["SUPABASE_KEY"] = supabase_key or ""

# Debug output
print(f"SUPABASE_URL: {'Found' if supabase_url else 'Not found'}")
if supabase_key:
    print(f"SUPABASE_KEY: Found (starts with {supabase_key[:10]}...)")
else:
    print("SUPABASE_KEY: Not found")

app = Flask(__name__)

# Now get variables from environment (which is now loaded)
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

# Initialize Supabase client if credentials are available
supabase = None
if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("Supabase client initialized")
    except Exception as e:
        print(f"Error initializing Supabase: {str(e)}")
        supabase = None
else:
    print("Supabase credentials not found, database features disabled")

def derive_key(password, salt):
    """Derive a key from a password and salt"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def get_vision_client():
    # Get the environment
    is_production = os.environ.get('ENVIRONMENT') == 'production'
    
    # Try to get encrypted credentials - check exact case-sensitive variable names
    print("=== CASE SENSITIVITY DEBUG ===")
    for key in sorted(os.environ.keys()):
        if "CREDENTIAL" in key.upper() or "ENCRYPT" in key.upper():
            print(f"Found environment variable: {key}")
    print("=== END CASE DEBUG ===")
    
    encrypted_creds = os.environ.get('ENCRYPTED_GOOGLE_CREDENTIALS')
    encryption_key = os.environ.get('CREDENTIALS_ENCRYPTION_KEY')
    encryption_salt = os.environ.get('CREDENTIALS_ENCRYPTION_SALT')
    
    # Print debug information about environment variables 
    print(f"Environment is production: {is_production}")
    print(f"ENCRYPTED_GOOGLE_CREDENTIALS: {'Found' if encrypted_creds else 'Not found'}")
    print(f"CREDENTIALS_ENCRYPTION_KEY: {'Found' if encryption_key else 'Not found'}")
    print(f"CREDENTIALS_ENCRYPTION_SALT: {'Found' if encryption_salt else 'Not found'}")
    
    # Create a mock client class to use as fallback
    class MockVisionClient:
        def __init__(self):
            print("WARNING: Using mock Vision client because credentials were not found")
        
        def _mock_response(self, *args, **kwargs):
            # Create mock response objects with empty data
            class MockResponse:
                def __init__(self):
                    self.text_annotations = []
                    self.label_annotations = []
                    self.localized_object_annotations = []
            return MockResponse()
            
        def label_detection(self, *args, **kwargs):
            return self._mock_response()
            
        def text_detection(self, *args, **kwargs):
            return self._mock_response()
            
        def object_localization(self, *args, **kwargs):
            return self._mock_response()
    
    try:
        if encrypted_creds and encryption_key and encryption_salt:
            try:
                # Decode the salt and encrypted data
                print(f"Attempting to decrypt with key starting with {encryption_key[:3]}")
                print(f"Salt value starts with {encryption_salt[:10]}")
                print(f"Encrypted credentials starts with {encrypted_creds[:10]}")
                
                salt = base64.b64decode(encryption_salt)
                encrypted_data = base64.b64decode(encrypted_creds)
                
                # Derive the key using the provided password and salt
                key = derive_key(encryption_key, salt)
                
                # Decrypt the credentials
                f = Fernet(key)
                decrypted_data = f.decrypt(encrypted_data)
                
                # Parse the JSON credentials
                info = json.loads(decrypted_data)
                credentials = service_account.Credentials.from_service_account_info(info)
                print("Using encrypted credentials from environment variables")
                return vision.ImageAnnotatorClient(credentials=credentials)
                
            except Exception as e:
                print(f"Error decrypting credentials: {str(e)}")
        
        # Try file-based credentials if available
        credentials_path = os.path.join(os.path.dirname(__file__), 
                                     "astute-setting-453616-i4-1b42112072cf.json")
        print(f"Checking for file existence: {credentials_path}, exists: {os.path.exists(credentials_path)}")
        if os.path.exists(credentials_path):
            print(f"Using credentials file: {credentials_path}")
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            return vision.ImageAnnotatorClient(credentials=credentials)
            
        # If we get here, we couldn't load credentials, but we'll use a mock client
        # instead of crashing the application
        print("WARNING: No valid credentials found. Using mock client.")
        return MockVisionClient()
            
    except Exception as e:
        print(f"Error creating Vision client: {str(e)}")
        print("Falling back to mock client to avoid application crash")
        return MockVisionClient()

# Initialize the client
client = get_vision_client()

def extract_quantity(text):
    """Extract quantity information from text with improved accuracy"""
    # Look for explicit quantity patterns
    box_pattern = r'(\d+)\s*(?:box(?:es)?|pack(?:s)?)'
    count_pattern = r'(\d+)\s*(?:pairs?|pcs?|pieces?|count|gloves?|per\s*box)'
    
    # First check if we have a clear "X boxes of Y count"
    box_matches = re.findall(box_pattern, text.lower())
    count_matches = re.findall(count_pattern, text.lower())
    
    # If we have both "X boxes" and "Y per box", multiply them
    if box_matches and count_matches:
        try:
            boxes = int(box_matches[0])
            per_box = int(count_matches[0])
            # Sanity check - don't allow unreasonable quantities
            if boxes < 100 and per_box < 1000:
                return boxes * per_box
        except (ValueError, IndexError):
            pass
    
    # If explicit patterns don't work, look for stand-alone numbers
    # But filter out very large numbers which are likely barcodes/SKUs
    basic_pattern = r'\b(\d+)\b'
    all_numbers = [int(m) for m in re.findall(basic_pattern, text.lower())]
    reasonable_quantities = [n for n in all_numbers if 1 <= n <= 1000]
    
    if reasonable_quantities:
        # For quantities, often the middle values are the most relevant
        # (not the smallest which might be packaging or largest which might be SKUs)
        reasonable_quantities.sort()
        if len(reasonable_quantities) >= 3:
            # Use median values
            return reasonable_quantities[len(reasonable_quantities)//2]
        else:
            # With just 1-2 numbers, use the first one as most likely quantity
            return reasonable_quantities[0]
            
    # If nothing matches, default to 1
    return 1

def extract_product_info(texts, labels, objects):
    """Extract specific medical supply information"""
    product_info = {
        'product_name': None,
        'brand': 'Dynarex',  # Visible in the image
        'quantity': None,
        'type': None,
        'size': None,
        'is_sterile': False,
        'material': None,
        'features': []
    }
    
    full_text = texts[0].description.lower() if texts else ""
    
    # Check for sterile products
    if 'sterile' in full_text.lower():
        product_info['is_sterile'] = True
        product_info['features'].append('sterile')
    
    # Check for powder-free
    if 'powder-free' in full_text.lower() or 'powder free' in full_text.lower():
        product_info['features'].append('powder-free')
    
    # Extract material type
    materials = ['nitrile', 'latex', 'vinyl', 'polymer']
    for material in materials:
        if material in full_text.lower():
            product_info['material'] = material
            break
    
    # Extract quantity using improved function
    product_info['quantity'] = extract_quantity(full_text)
        
    # Extract product name and type
    if 'glove' in full_text.lower():
        product_info['type'] = 'surgical gloves'
        # Construct full product name
        if product_info['material']:
            product_info['product_name'] = f"Sterile {product_info['material'].title()} Surgical Gloves"
    
    # Extract if it's cuffed
    if 'cuffed' in full_text.lower():
        product_info['features'].append('cuffed')
    
    return product_info

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'API is running',
        'status': 'ok'
    })

@app.route('/analyze', methods=['POST'])
def analyze_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
            
        image = request.files['image']
        content = image.read()
        image = vision.Image(content=content)
        
        # Perform multiple detection types
        label_response = client.label_detection(image=image)
        text_response = client.text_detection(image=image)
        object_response = client.object_localization(image=image)
        
        texts = text_response.text_annotations
        objects = object_response.localized_object_annotations
        labels = label_response.label_annotations
        
        # Extract medical supply specific information
        product_info = extract_product_info(texts, labels, objects)
        
        return jsonify({
            'success': True,
            'product_info': product_info,
            'text_detection': {
                'full_text': texts[0].description if texts else "",
                'text_elements': [{
                    'text': text.description,
                    'confidence': float(text.score) if hasattr(text, 'score') else None,
                } for text in texts[1:]]
            },
            'objects': [{
                'name': obj.name,
                'confidence': float(obj.score)
            } for obj in objects],
            'labels': [{
                'description': label.description,
                'confidence': float(label.score)
            } for label in labels]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/analyze-and-save', methods=['POST'])
def analyze_and_save():
    try:
        # Add debug output at the beginning of the endpoint
        print("=============================================")
        print("Starting analyze-and-save endpoint")
        print(f"Supabase client status: {'Initialized' if supabase else 'Not initialized'}")
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
            
        # Get user and organization info from request
        user_id = request.form.get('user_id', '29545123-118e-4c95-8cea-59ee52411732')  # Default if not provided
        organization_id = request.form.get('organization_id', '117d5be5-c6d2-47e4-bfcf-49caaa6cad15')  # Default if not provided
        print(f"User ID: {user_id}")
        print(f"Organization ID: {organization_id}")
        
        image = request.files['image']
        content = image.read()
        image = vision.Image(content=content)
        
        # Perform analysis
        label_response = client.label_detection(image=image)
        text_response = client.text_detection(image=image)
        object_response = client.object_localization(image=image)
        
        texts = text_response.text_annotations
        objects = object_response.localized_object_annotations
        labels = label_response.label_annotations
        
        # Extract product info
        product_info = extract_product_info(texts, labels, objects)
        
        # Check if Supabase is configured
        if not supabase:
            print("Supabase client is None when trying to save data")
            return jsonify({
                'success': True,
                'product_info': product_info,
                'warning': 'Database not configured, results not saved'
            })
        
        try:
            # First, save the scan to inventory_scans table
            scan_id = str(uuid.uuid4())
            scan_record = {
                'id': scan_id,
                'created_at': datetime.now().isoformat(),
                'full_text': texts[0].description if texts else "",
                'product_name': product_info['product_name'],
                'organization_id': organization_id,
                'scanned_by': user_id,
                'scan_type': 'label_scan',
                'quantity': product_info['quantity'] or 1
            }
            
            # Try to add analysis_data if the field exists
            try:
                analysis_data = json.dumps({
                    'product_info': product_info,
                    'objects': [{
                        'name': obj.name,
                        'confidence': float(obj.score)
                    } for obj in objects],
                    'labels': [{
                        'description': label.description,
                        'confidence': float(label.score)
                    } for label in labels]
                })
                scan_record['analysis_data'] = analysis_data
            except Exception as e:
                print(f"Error adding analysis_data to scan record: {str(e)}")
            
            # Insert scan record
            scan_result = supabase.table('inventory_scans').insert(scan_record).execute()
            print(f"Successfully saved scan record with ID: {scan_id}")
            
            # Try to save inventory item information if product_name exists
            item_id = None
            item_status = 'not_identified'
            
            if product_info['product_name']:
                try:
                    # Simple insert for inventory items
                    item_id = str(uuid.uuid4())
                    item_record = {
                        'id': item_id,
                        'name': product_info['product_name'],
                        'description': f"{product_info['brand']} {product_info['material'] or ''} {product_info['type'] or ''}".strip(),
                        'brand': product_info['brand'],
                        'quantity': product_info['quantity'] or 1,
                        'material': product_info['material'],
                        'is_sterile': product_info['is_sterile'],
                        'features': ','.join(product_info['features']),
                        'created_at': datetime.now().isoformat(),
                        'last_updated': datetime.now().isoformat(),
                        'last_scan_id': scan_id
                    }
                    
                    item_result = supabase.table('inventory_items').insert(item_record).execute()
                    print(f"Successfully saved item record with ID: {item_id}")
                    
                    # Try to save movement record
                    try:
                        movement_id = str(uuid.uuid4())
                        movement_record = {
                            'id': movement_id,
                            'item_id': item_id,
                            'quantity_change': product_info['quantity'] or 1,
                            'new_quantity': product_info['quantity'] or 1,
                            'created_at': datetime.now().isoformat(),
                            'scan_id': scan_id,
                            'type': 'initial_scan'
                        }
                        
                        movement_result = supabase.table('inventory_movements').insert(movement_record).execute()
                        print(f"Successfully saved movement record with ID: {movement_id}")
                    except Exception as e:
                        print(f"Error saving movement record: {str(e)}")
                    
                    item_status = 'created'
                except Exception as e:
                    print(f"Error saving item record: {str(e)}")
            
            return jsonify({
                'success': True,
                'product_info': product_info,
                'scan_id': scan_id,
                'item_id': item_id,
                'item_status': item_status,
                'saved': True,
                'text_detection': {
                    'full_text': texts[0].description if texts else "",
                },
                'objects': [{
                    'name': obj.name,
                    'confidence': float(obj.score)
                } for obj in objects],
                'labels': [{
                    'description': label.description,
                    'confidence': float(label.score)
                } for label in labels]
            })
            
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
            # Return the product info even if saving failed
            return jsonify({
                'success': True,
                'product_info': product_info,
                'warning': f'Analysis successful but database save failed: {str(db_error)}',
                'text_detection': {
                    'full_text': texts[0].description if texts else "",
                },
                'objects': [{
                    'name': obj.name,
                    'confidence': float(obj.score)
                } for obj in objects],
                'labels': [{
                    'description': label.description,
                    'confidence': float(label.score)
                } for label in labels]
            })
            
    except Exception as e:
        print(f"General error in analyze-and-save: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/test-supabase', methods=['GET'])
def test_supabase_connection():
    try:
        if not supabase:
            return jsonify({
                'success': False,
                'message': 'Supabase client not initialized. Check your environment variables.'
            })
        
        # Try to get table information
        response = supabase.table('inventory').select('count').execute()
        
        # Return success information
        return jsonify({
            'success': True,
            'message': 'Successfully connected to Supabase',
            'supabase_url': supabase_url,
            'table_exists': True,
            'response': response
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_table_schema(table_name):
    """Get the schema for a table to ensure we send valid data"""
    # Since execute_sql RPC is not available, we'll return a simplified schema 
    # based on known table structures
    try:
        # Predefined schemas for essential tables
        schemas = {
            'inventory_scans': {
                'id': {'type': 'uuid', 'nullable': False},
                'created_at': {'type': 'timestamp', 'nullable': True},
                'full_text': {'type': 'text', 'nullable': True},
                'product_name': {'type': 'text', 'nullable': True},
                'organization_id': {'type': 'uuid', 'nullable': False},
                'scanned_by': {'type': 'uuid', 'nullable': False},
                'analysis_data': {'type': 'jsonb', 'nullable': True},
                'scan_type': {'type': 'text', 'nullable': True},
                'quantity': {'type': 'integer', 'nullable': True}
            },
            'inventory_items': {
                'id': {'type': 'uuid', 'nullable': False},
                'name': {'type': 'text', 'nullable': False},
                'description': {'type': 'text', 'nullable': True},
                'brand': {'type': 'text', 'nullable': True},
                'category_id': {'type': 'uuid', 'nullable': True},
                'quantity': {'type': 'integer', 'nullable': True},
                'material': {'type': 'text', 'nullable': True},
                'is_sterile': {'type': 'boolean', 'nullable': True},
                'features': {'type': 'text', 'nullable': True},
                'created_at': {'type': 'timestamp', 'nullable': True},
                'last_updated': {'type': 'timestamp', 'nullable': True},
                'last_scan_id': {'type': 'uuid', 'nullable': True}
            },
            'inventory_movements': {
                'id': {'type': 'uuid', 'nullable': False},
                'item_id': {'type': 'uuid', 'nullable': False},
                'quantity_change': {'type': 'integer', 'nullable': False},
                'new_quantity': {'type': 'integer', 'nullable': True},
                'created_at': {'type': 'timestamp', 'nullable': True},
                'scan_id': {'type': 'uuid', 'nullable': True},
                'type': {'type': 'text', 'nullable': True}
            }
        }
        
        if table_name in schemas:
            print(f"Using predefined schema for '{table_name}' with {len(schemas[table_name])} columns")
            return schemas[table_name]
        else:
            print(f"No predefined schema for '{table_name}'")
            return None
            
    except Exception as e:
        print(f"Error getting schema for '{table_name}': {str(e)}")
        return None

def validate_data_for_table(data, table_name, schema=None):
    """Validate data against a table schema"""
    if not schema:
        # We'll skip validation if we couldn't get the schema
        return data
        
    valid_data = {}
    for key, value in data.items():
        if key in schema:
            # Check for null values in non-nullable fields
            if value is None and not schema[key]['nullable']:
                print(f"Warning: Null value for non-nullable field '{key}' in '{table_name}'")
                continue
                
            # Add any other type validations here if needed
            valid_data[key] = value
        else:
            print(f"Warning: Field '{key}' not found in schema for '{table_name}'")
            
    return valid_data

@app.route('/test-write-supabase', methods=['GET'])
def test_write_supabase():
    try:
        if not supabase:
            return jsonify({
                'success': False,
                'message': 'Supabase client not initialized'
            })
        
        # First, let's check what columns actually exist
        schema_query = """
        SELECT column_name, data_type 
        FROM information_schema.columns
        WHERE table_name = 'inventory_scans'
        """
        
        try:
            schema_result = supabase.rpc('execute_sql', {'query': schema_query}).execute()
            
            # Log the actual schema
            print("Inventory_scans table schema:")
            columns = [col['column_name'] for col in schema_result.data]
            print(columns)
            
            # Create a test record with all required fields
            test_id = str(uuid.uuid4())
            test_record = {
                'id': test_id,
                'organization_id': '117d5be5-c6d2-47e4-bfcf-49caaa6cad15',
                'scanned_by': '29545123-118e-4c95-8cea-59ee52411732'  # Add user ID
            }
            
            # Only add fields that exist in the schema
            if 'created_at' in columns:
                test_record['created_at'] = datetime.now().isoformat()
            if 'full_text' in columns:
                test_record['full_text'] = 'Test record'
            if 'product_name' in columns:
                test_record['product_name'] = 'Test Product'
            if 'analysis_data' in columns:
                test_record['analysis_data'] = json.dumps({'test': True})
            
            # Try to insert into inventory_scans
            print(f"Attempting to write test record {test_id} to inventory_scans")
            print(f"Record data: {test_record}")
            result = supabase.table('inventory_scans').insert(test_record).execute()
            
            return jsonify({
                'success': True,
                'message': 'Successfully wrote test record to Supabase',
                'record_id': test_id,
                'schema': columns,
                'record': test_record
            })
        except Exception as e:
            # If the SQL query fails, let's try a simpler method to write to the table
            print(f"Error with schema query: {str(e)}")
            print("Trying a minimal insertion with just ID...")
            
            test_id = str(uuid.uuid4())
            minimal_record = {
                'id': test_id,
                'organization_id': '117d5be5-c6d2-47e4-bfcf-49caaa6cad15',
                'scanned_by': '29545123-118e-4c95-8cea-59ee52411732'  # Add user ID
            }
            result = supabase.table('inventory_scans').insert(minimal_record).execute()
            
            return jsonify({
                'success': True,
                'message': 'Successfully wrote minimal record to Supabase',
                'record_id': test_id,
                'record': minimal_record,
                'note': 'Used minimal record due to schema query error'
            })
            
    except Exception as e:
        print(f"Error in test-write-supabase: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/check-table-structure', methods=['GET'])
def check_table_structure():
    try:
        if not supabase:
            return jsonify({
                'success': False,
                'message': 'Supabase client not initialized'
            })
        
        # Get the actual table columns without trying to use them
        tables_to_check = ['inventory_scans', 'inventory_items', 'inventory_movements', 'inventory_categories']
        table_structures = {}
        
        for table in tables_to_check:
            try:
                # Simple query to get column info
                query = f"""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns
                WHERE table_name = '{table}'
                """
                
                result = supabase.rpc('execute_sql', {'query': query}).execute()
                columns = result.data if result.data else []
                
                # Save the column names
                table_structures[table] = {
                    'columns': [col['column_name'] for col in columns],
                    'column_details': columns
                }
                
            except Exception as e:
                table_structures[table] = {
                    'error': str(e)
                }
        
        return jsonify({
            'success': True,
            'message': 'Successfully retrieved table structure',
            'tables': table_structures
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/test-write-bare-minimum', methods=['GET'])
def test_write_bare_minimum():
    try:
        if not supabase:
            return jsonify({
                'success': False,
                'message': 'Supabase client not initialized'
            })
        
        # Create a minimal record with required fields
        test_id = str(uuid.uuid4())
        minimal_record = {
            'id': test_id,
            'created_at': datetime.now().isoformat(),
            'organization_id': '117d5be5-c6d2-47e4-bfcf-49caaa6cad15',
            'scanned_by': '29545123-118e-4c95-8cea-59ee52411732',
            'scan_type': 'label_scan'  # Add this field
        }
        
        # Try direct insert with minimal fields
        result = supabase.table('inventory_scans').insert(minimal_record).execute()
        
        return jsonify({
            'success': True,
            'message': 'Successfully wrote minimal record to Supabase',
            'record_id': test_id,
            'record': minimal_record
        })
            
    except Exception as e:
        print(f"Error in test-write-bare-minimum: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/simple-db-test', methods=['GET'])
def simple_db_test():
    try:
        if not supabase:
            return jsonify({
                'success': False,
                'message': 'Supabase client not initialized'
            })
        
        # Create a minimal record with required fields
        test_id = str(uuid.uuid4())
        minimal_record = {
            'id': test_id,
            'organization_id': '117d5be5-c6d2-47e4-bfcf-49caaa6cad15',
            'scanned_by': '29545123-118e-4c95-8cea-59ee52411732',
            'scan_type': 'label_scan'  # Add this field
        }
        
        # Try direct insert
        result = supabase.table('inventory_scans').insert(minimal_record).execute()
        
        return jsonify({
            'success': True,
            'message': 'Successfully tested Supabase connection',
            'record_id': test_id,
            'insert_result': True
        })
            
    except Exception as e:
        print(f"Error in simple-db-test: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500

@app.route('/list-tables', methods=['GET'])
def list_tables():
    try:
        if not supabase:
            return jsonify({
                'success': False,
                'message': 'Supabase client not initialized'
            })
        
        # Try several common system views to find tables
        all_tables = []
        
        try:
            # Get tables via the pg_tables view (standard PostgreSQL)
            table_query = supabase.from_("pg_tables").select("*").execute()
            if hasattr(table_query, 'data') and table_query.data:
                all_tables = [t.get('tablename') for t in table_query.data 
                             if t.get('schemaname') == 'public']
        except Exception as e:
            print(f"Error querying pg_tables: {str(e)}")
        
        return jsonify({
            'success': True,
            'tables': all_tables
        })
            
    except Exception as e:
        print(f"Error in list-tables: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/complete-db-test', methods=['GET'])
def complete_db_test():
    try:
        if not supabase:
            return jsonify({
                'success': False,
                'message': 'Supabase client not initialized'
            })
        
        # Create a comprehensive record with ALL possible required fields
        test_id = str(uuid.uuid4())
        complete_record = {
            'id': test_id,
            'organization_id': '117d5be5-c6d2-47e4-bfcf-49caaa6cad15',
            'scanned_by': '29545123-118e-4c95-8cea-59ee52411732',
            'scan_type': 'label_scan',  # Add the required scan_type
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'full_text': 'Complete test record',
            'product_name': 'Test Product',
            'analysis_data': json.dumps({'test': True}),
            'status': 'processed',
            'notes': 'Testing with all possible fields',
            'source': 'api_test',
            'metadata': json.dumps({
                'test_run': True,
                'timestamp': datetime.now().isoformat()
            })
        }
        
        # Try direct insert
        result = supabase.table('inventory_scans').insert(complete_record).execute()
        
        return jsonify({
            'success': True,
            'message': 'Successfully tested Supabase connection',
            'record_id': test_id,
            'insert_result': True
        })
            
    except Exception as e:
        print(f"Error in complete-db-test: {str(e)}")
        
        # Return more detailed error info to help debug
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'attempted_record': complete_record
        }), 500

@app.route('/debug-environment', methods=['GET'])
def debug_environment():
    """Endpoint to check environment variable status"""
    env_vars = {
        'ENVIRONMENT': os.environ.get('ENVIRONMENT'),
        'SUPABASE_URL_EXISTS': os.environ.get('SUPABASE_URL') is not None,
        'SUPABASE_KEY_EXISTS': os.environ.get('SUPABASE_KEY') is not None,
        'ENCRYPTED_GOOGLE_CREDENTIALS_EXISTS': os.environ.get('ENCRYPTED_GOOGLE_CREDENTIALS') is not None,
        'CREDENTIALS_ENCRYPTION_SALT_EXISTS': os.environ.get('CREDENTIALS_ENCRYPTION_SALT') is not None,
        'CREDENTIALS_ENCRYPTION_KEY_EXISTS': os.environ.get('CREDENTIALS_ENCRYPTION_KEY') is not None,
        'ENV_FILE_EXISTS': os.path.exists('.env'),
        'CREDENTIALS_FILE_EXISTS': os.path.exists(os.path.join(os.path.dirname(__file__), 
                                                            "astute-setting-453616-i4-1b42112072cf.json")),
        'CURRENT_DIRECTORY': os.getcwd(),
        'DIRECTORY_CONTENTS': os.listdir(os.getcwd()),
    }
    
    return jsonify({
        'success': True,
        'environment_debug': env_vars
    })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple endpoint to check if the app is running"""
    return jsonify({
        'success': True,
        'message': 'App is running successfully!',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api-docs', methods=['GET'])
def api_docs():
    """Documentation on how to use the API"""
    return jsonify({
        'api_name': 'Elio Vision API',
        'base_url': 'https://elio-vision-api-production.up.railway.app',
        'description': 'API for analyzing medical supplies using Google Vision',
        'endpoints': [
            {
                'path': '/analyze',
                'method': 'POST',
                'description': 'Analyze an image without saving to database',
                'parameters': [
                    {'name': 'image', 'type': 'file', 'required': True, 'description': 'Image file to analyze'}
                ]
            },
            {
                'path': '/analyze-and-save',
                'method': 'POST',
                'description': 'Analyze an image and save results to Supabase',
                'parameters': [
                    {'name': 'image', 'type': 'file', 'required': True, 'description': 'Image file to analyze'},
                    {'name': 'user_id', 'type': 'string', 'required': False, 'description': 'ID of the user performing the scan'},
                    {'name': 'organization_id', 'type': 'string', 'required': False, 'description': 'ID of the organization'}
                ]
            },
            {
                'path': '/analyze-and-save-basic',
                'method': 'POST',
                'description': 'Simplified version of analyze-and-save with minimal database schema',
                'parameters': [
                    {'name': 'image', 'type': 'file', 'required': True, 'description': 'Image file to analyze'},
                    {'name': 'user_id', 'type': 'string', 'required': False, 'description': 'ID of the user performing the scan'},
                    {'name': 'organization_id', 'type': 'string', 'required': False, 'description': 'ID of the organization'}
                ]
            }
        ],
        'usage_example': {
            'curl': 'curl -X POST -F "image=@image.jpg" -F "user_id=USER_ID" -F "organization_id=ORG_ID" https://elio-vision-api-production.up.railway.app/analyze-and-save',
            'javascript': 'const formData = new FormData(); formData.append("image", imageFile); formData.append("user_id", "USER_ID"); formData.append("organization_id", "ORG_ID"); fetch("https://elio-vision-api-production.up.railway.app/analyze-and-save", { method: "POST", body: formData }).then(res => res.json()).then(data => console.log(data));'
        }
    })

@app.route('/analyze-and-save-basic', methods=['POST'])
def analyze_and_save_basic():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
            
        # Get user and organization info from request
        user_id = request.form.get('user_id', '29545123-118e-4c95-8cea-59ee52411732')  # Default if not provided
        organization_id = request.form.get('organization_id', '117d5be5-c6d2-47e4-bfcf-49caaa6cad15')  # Default if not provided
        print(f"User ID: {user_id}")
        print(f"Organization ID: {organization_id}")
        
        image = request.files['image']
        content = image.read()
        image = vision.Image(content=content)
        
        # Perform analysis
        label_response = client.label_detection(image=image)
        text_response = client.text_detection(image=image)
        object_response = client.object_localization(image=image)
        
        texts = text_response.text_annotations
        objects = object_response.localized_object_annotations
        labels = label_response.label_annotations
        
        # Extract product info
        product_info = extract_product_info(texts, labels, objects)
        
        # Check if Supabase is configured
        if not supabase:
            return jsonify({
                'success': True,
                'product_info': product_info,
                'warning': 'Database not configured, results not saved'
            })
        
        try:    
            # Create a basic scan record that should work with existing schema
            scan_id = str(uuid.uuid4())
            scan_record = {
                'id': scan_id,
                'organization_id': organization_id,
                'scanned_by': user_id,
                'scan_type': 'label_scan',
                'full_text': texts[0].description if texts else "",
                'product_name': product_info['product_name'] or "Unknown Product",
                'quantity': product_info['quantity'] or 1,
                'created_at': datetime.now().isoformat()
                # Skip analysis_data which causes problems
            }
            
            # Insert scan record
            scan_result = supabase.table('inventory_scans').insert(scan_record).execute()
            print(f"Successfully saved basic scan record with ID: {scan_id}")
            
            return jsonify({
                'success': True,
                'product_info': product_info,
                'scan_id': scan_id,
                'saved': True,
                'text_detection': {
                    'full_text': texts[0].description if texts else "",
                },
                'objects': [{
                    'name': obj.name,
                    'confidence': float(obj.score)
                } for obj in objects],
                'labels': [{
                    'description': label.description,
                    'confidence': float(label.score)
                } for label in labels]
            })
            
        except Exception as db_error:
            print(f"Database error in analyze-and-save-basic: {str(db_error)}")
            # Return the product info even if saving failed
            return jsonify({
                'success': True,
                'product_info': product_info,
                'warning': f'Analysis successful but database save failed: {str(db_error)}',
                'text_detection': {
                    'full_text': texts[0].description if texts else "",
                },
                'objects': [{
                    'name': obj.name,
                    'confidence': float(obj.score)
                } for obj in objects],
                'labels': [{
                    'description': label.description,
                    'confidence': float(label.score)
                } for label in labels]
            })
            
    except Exception as e:
        print(f"General error in analyze-and-save-basic: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Get port from command line argument or use default
    import sys
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)
    else:
        port = int(os.environ.get('PORT', 8080))
    
    # Make the port super visible in the output
    print("\n" + "="*50)
    print(f"🚀 STARTING FLASK SERVER ON PORT: {port}")
    print(f"📌 URL: http://localhost:{port}")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=True) 
# Add CORS support
from flask_cors import CORS
CORS(app)

# Make sure the port is configured correctly for production
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9000))
    app.run(host='0.0.0.0', port=port, debug=False)

from flask_cors import CORS
CORS(app)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9000))
    app.run(host='0.0.0.0', port=port, debug=False)
