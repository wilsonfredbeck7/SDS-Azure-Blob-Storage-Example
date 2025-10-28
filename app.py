from flask import Flask, request, jsonify, render_template
from azure.storage.blob import BlobServiceClient
import os
from datetime import datetime
import re

app = Flask(__name__)

# Configuration
STORAGE_ACCOUNT_URL = os.getenv('STORAGE_ACCOUNT_URL')
IMAGES_CONTAINER = os.getenv('IMAGES_CONTAINER', 'lanternfly-images')
connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')

# Create Blob Service Client
bsc = BlobServiceClient.from_connection_string(connect_str)
cc = bsc.get_container_client(IMAGES_CONTAINER)

def sanitize_filename(filename):
    """Sanitize filename and prepend ISO timestamp"""
    # Remove any path components
    filename = os.path.basename(filename)
    # Remove special characters except dots and hyphens
    filename = re.sub(r'[^a-zA-Z0-9.-]', '_', filename)
    # Prepend ISO timestamp
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
    return f"{timestamp}-{filename}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/v1/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/api/v1/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({"ok": False, "error": "No file provided"}), 400
        
        f = request.files['file']
        if f.filename == '':
            return jsonify({"ok": False, "error": "No file selected"}), 400
        
        # Check if it's an image file
        if not f.content_type or not f.content_type.startswith('image/'):
            return jsonify({"ok": False, "error": "Only image files are allowed"}), 400
        
        # Sanitize filename and add timestamp
        filename = sanitize_filename(f.filename)
        
        # Upload to blob storage
        blob_client = bsc.get_blob_client(container=IMAGES_CONTAINER, blob=filename)
        blob_client.upload_blob(f, overwrite=True)
        
        # Return success response with URL
        return jsonify({"ok": True, "url": f"{cc.url}/{filename}"}), 200
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/v1/gallery', methods=['GET'])
def gallery():
    try:
        # List all blobs in the container
        blob_list = cc.list_blobs()
        gallery_urls = []
        
        for blob in blob_list:
            # Create public URL for each blob
            gallery_urls.append(f"{cc.url}/{blob.name}")
        
        return jsonify({"ok": True, "gallery": gallery_urls}), 200
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500