from flask import Flask, request, render_template, redirect, url_for, flash
from azure.storage.blob import BlobServiceClient
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for flashing messages

# Azure Storage connection
connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
blob_service_client = BlobServiceClient.from_connection_string(connect_str)
container_name = "uploads"

# Ensure container exists
try:
    blob_service_client.create_container(container_name)
except Exception:
    pass  # container likely already exists

@app.route('/')
def index():
    return render_template('index.html', container=container_name, config=app.config)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash("No file part", "error")
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash("No selected file", "error")
        return redirect(url_for('index'))

    try:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file.filename)
        blob_client.upload_blob(file, overwrite=True)
        flash(f"File '{file.filename}' uploaded successfully!", "success")
    except Exception as e:
        flash(f"Upload failed: {str(e)}", "error")

    return redirect(url_for('index'))

@app.route('/files')
def files():
    container_client = blob_service_client.get_container_client(container_name)
    blob_list = container_client.list_blobs()
    return render_template('files.html', blobs=blob_list)

@app.route('/api/v1/health')
def health():
    return {"ok": True, "status": "healthy"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)


