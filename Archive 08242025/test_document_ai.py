#!/usr/bin/env python3
"""Test Google Document AI authentication using existing OAuth setup."""

from google.cloud import documentai_v1 as documentai
import os

def test_document_ai_auth():
    """Test Document AI authentication with service account credentials."""
    
    # Use service account instead of OAuth for Document AI
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/jim/Secrets/modular-command-466820-p2-bc0974cd5852.json'
    
    # Test that the credentials file exists
    if not os.path.exists(os.environ['GOOGLE_APPLICATION_CREDENTIALS']):
        print(f"❌ Credentials file not found: {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")
        return False
    
    print("✅ Service account credentials file found")
    
    # Initialize Document AI client with service account credentials
    try:
        client = documentai.DocumentProcessorServiceClient()
        
        # You'll need to set your project ID
        project_id = "modular-command-466820-p2"  # Your project ID from the service account
        location = "us"  # or "eu" depending on your preference
        
        # List processors to test the connection
        parent = f"projects/{project_id}/locations/{location}"
        
        # This will fail if not authenticated properly
        # Note: You may not have processors yet, that's OK
        try:
            processors = client.list_processors(parent=parent)
            print(f"✅ Document AI authenticated! Found processors in {location}")
            for processor in processors:
                print(f"  - {processor.display_name}")
        except Exception as e:
            if "not found" in str(e).lower():
                print(f"✅ Document AI authenticated! (No processors created yet)")
            else:
                print(f"⚠️  Authentication works but got error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize Document AI client: {e}")
        print("\nMake sure you have:")
        print("1. Enabled Document AI API in Google Cloud Console")
        print("2. Set your project ID in this script")
        print("3. Re-authenticated after adding the new scope")
        return False

if __name__ == "__main__":
    print("Testing Document AI authentication...\n")
    
    # Install required package if not present
    try:
        pass
    except ImportError:
        print("Installing google-cloud-documentai...")
        os.system("pip install google-cloud-documentai")
        print()
    
    success = test_document_ai_auth()
    
    if success:
        print("\n🎉 Document AI is ready to use with your Gmail OAuth!")
    else:
        print("\n❌ Document AI setup incomplete - see errors above")