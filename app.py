from flask import Flask, request, render_template, redirect, url_for
from azure.storage.blob import BlobServiceClient
import os

app = Flask(__name__)

connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')

blob_service_client = BlobServiceClient.from_connection_string(connect_str)
container_name = "uploads"

@app.route('/')
def index():
    return render_template('index.html')

from flask import jsonify

@app.route('/api/v1/health', methods=['GET'])
def api_health():
    return jsonify({"status": "ok"}), 200

@app.route('/api/v1/upload', methods=['POST'])
def api_upload():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({"success": False, "error": "No file provided"}), 400

        # Check if Azure connection is available
        if not connect_str:
            return jsonify({"success": False, "error": "Azure storage not configured"}), 500

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file.filename)
        blob_client.upload_blob(file, overwrite=True)

        return jsonify({"status": "success", "filename": file.filename}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({"success": False, "error": "No file provided"}), 400

        # Check if Azure connection is available
        if not connect_str:
            return jsonify({"success": False, "error": "Azure storage not configured"}), 500

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file.filename)
        blob_client.upload_blob(file, overwrite=True)

        return jsonify({"filename": file.filename, "success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/files')
def files():
    try:
        if not connect_str:
            return jsonify({"error": "Azure storage not configured"}), 500
            
        container_client = blob_service_client.get_container_client(container_name)
        blob_list = container_client.list_blobs()
        return render_template('files.html', blobs=blob_list, container=container_name)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/sas/<blob_name>')
def sas_for_blob(blob_name):
    return f"SAS link for {blob_name} would go here"

