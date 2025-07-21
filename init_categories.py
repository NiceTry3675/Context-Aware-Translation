import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY")

if not ADMIN_SECRET_KEY:
    print("Error: ADMIN_SECRET_KEY not found in environment variables")
    exit(1)

# Initialize categories
def init_categories():
    """Initialize default post categories"""
    endpoint = f"{API_URL}/api/v1/admin/community/init-categories"
    
    headers = {
        "X-Admin-Secret": ADMIN_SECRET_KEY
    }
    
    print(f"Initializing categories at {endpoint}...")
    
    try:
        response = requests.post(endpoint, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data['message']}")
            
            if data.get('categories'):
                print("\nCreated categories:")
                for cat in data['categories']:
                    print(f"  - {cat['display_name']} ({cat['name']})")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Failed to initialize categories: {e}")

if __name__ == "__main__":
    print("=== Community Board Category Initialization ===\n")
    init_categories()
    print("\n✨ Done!") 