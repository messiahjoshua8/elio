from google.cloud import vision
import os
import json
from google.oauth2 import service_account

def analyze_image(image_path):
    # Set up the client with explicit credentials
    credentials_path = os.path.join(os.path.dirname(__file__), 
                                  "astute-setting-453616-i4-1b42112072cf.json")
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    client = vision.ImageAnnotatorClient(credentials=credentials)
    
    # Read the image file
    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    
    # Perform different detection types
    label_response = client.label_detection(image=image)
    text_response = client.text_detection(image=image)
    object_response = client.object_localization(image=image)
    
    # Extract the text
    texts = text_response.text_annotations
    full_text = texts[0].description if texts else ""
    
    # Extract objects
    objects = object_response.localized_object_annotations
    object_list = [{
        'name': obj.name,
        'confidence': float(obj.score)
    } for obj in objects]
    
    # Extract labels
    labels = label_response.label_annotations
    label_list = [{
        'description': label.description,
        'confidence': float(label.score)
    } for label in labels]
    
    # Format the results
    results = {
        'text': full_text,
        'objects': object_list,
        'labels': label_list
    }
    
    # Print formatted results
    print("===== VISION API RESULTS =====")
    print("\n=== TEXT DETECTED ===")
    print(full_text)
    
    print("\n=== OBJECTS DETECTED ===")
    for obj in object_list:
        print(f"Object: {obj['name']}, Confidence: {obj['confidence']:.2f}")
    
    print("\n=== LABELS DETECTED ===")
    for label in label_list:
        print(f"Label: {label['description']}, Confidence: {label['confidence']:.2f}")
    
    return results

if __name__ == "__main__":
    # Make sure to set your credentials environment variable
    # export GOOGLE_APPLICATION_CREDENTIALS="astute-setting-453616-i4-1b42112072cf.json"
    
    # Path to your test image
    image_path = "test_image.jpg"
    
    # Analyze the image
    results = analyze_image(image_path)
    
    # Optionally save results to a file
    with open("vision_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nResults also saved to vision_results.json") 