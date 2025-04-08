import requests
import json
import os
import sys
from pathlib import Path

base_url = "http://localhost:9000"  # Correct port

def test_analyze_endpoint(image_path, url=None):
    """Test the /analyze endpoint with an image"""
    if url is None:
        url = f"{base_url}/analyze"  # Use base_url
        
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return
    
    print(f"Testing /analyze endpoint with image: {image_path}")
    
    # Prepare the file for upload
    files = {'image': open(image_path, 'rb')}
    
    try:
        # Send the request
        print(f"Sending request to {url}...")
        response = requests.post(url, files=files)
        
        # Check the result
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Request successful!")
            print(f"Status code: {response.status_code}")
            
            # Print formatted JSON response
            print("\nResponse:")
            print(json.dumps(result, indent=2))
            
            # Save the results to a file
            output_file = f"analyze_result_{Path(image_path).stem}.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nResults saved to {output_file}")
            
            return result
        else:
            print(f"\n❌ Request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None

def test_analyze_and_save_endpoint(image_path, url=None):
    """Test the /analyze-and-save endpoint with an image"""
    if url is None:
        url = f"{base_url}/analyze-and-save"  # Use base_url
        
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return
    
    print(f"Testing /analyze-and-save endpoint with image: {image_path}")
    
    # Prepare the file for upload
    files = {'image': open(image_path, 'rb')}
    
    try:
        # Send the request
        print(f"Sending request to {url}...")
        response = requests.post(url, files=files)
        
        # Check the result
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Request successful!")
            print(f"Status code: {response.status_code}")
            
            # Print formatted JSON response
            print("\nResponse:")
            print(json.dumps(result, indent=2))
            
            # Print specifically about database results
            if result.get('saved'):
                print("\nDatabase actions:")
                print(f"- Scan ID: {result.get('scan_id')}")
                print(f"- Item Status: {result.get('item_status')}")
                if result.get('item_id'):
                    print(f"- Item ID: {result.get('item_id')}")
            
            # Save the results to a file
            output_file = f"analyze_save_result_{Path(image_path).stem}.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nResults saved to {output_file}")
            
            return result
        else:
            print(f"\n❌ Request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None

if __name__ == "__main__":
    # Check if an image path was provided
    if len(sys.argv) < 2:
        print("Usage: python test_api.py <path_to_image> [endpoint]")
        print("\nExample:")
        print("  python test_api.py sample_image.jpg")
        print("  python test_api.py sample_image.jpg analyze-and-save")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    # Check if a specific endpoint was requested
    endpoint = "both"
    if len(sys.argv) >= 3:
        endpoint = sys.argv[2]
    
    # Start the Flask server in a separate process if it's not already running
    # For now, we assume the server is already running
    
    # Run the tests
    if endpoint == "analyze" or endpoint == "both":
        test_analyze_endpoint(image_path)
        
    if endpoint == "analyze-and-save" or endpoint == "both":
        if endpoint == "both":
            print("\n" + "-"*50 + "\n")
        test_analyze_and_save_endpoint(image_path) 