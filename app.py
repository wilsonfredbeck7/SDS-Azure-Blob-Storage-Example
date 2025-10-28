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

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=file.filename)
            blob_client.upload_blob(file, overwrite=True)
            return redirect(url_for('files'))
    return render_template('upload.html')

@app.route('/files')
def files():
    container_client = blob_service_client.get_container_client(container_name)
    blob_list = container_client.list_blobs()
    return render_template('files.html', blobs=blob_list, container=container_name)

@app.route('/sas/<blob_name>')
def sas_for_blob(blob_name):
    return f"SAS link for {blob_name} would go here"

