import os
import mimetypes
import datetime as dt
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from azure.storage.blob import BlobServiceClient, ContentSettings

# --- Config ---
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "lanternfly-images")
MAX_CONTENT_MB = int(os.getenv("MAX_CONTENT_MB", "10"))  # max 10 MB for Lanternfly

if not AZURE_STORAGE_CONNECTION_STRING:
    raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is not set. Put it in .env or environment.")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_MB * 1024 * 1024  # enforce size limit

# Initialize Blob Service Client
bsc = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = bsc.get_container_client(CONTAINER_NAME)

# Ensure container exists
try:
    container_client.create_container()
except Exception:
    pass  # container already exists

# --- Helpers ---
def _content_settings_for(filename: str) -> ContentSettings:
    ctype, _ = mimetypes.guess_type(filename)
    return ContentSettings(content_type=ctype or "application/octet-stream")

def _make_blob_name(filename: str) -> str:
    safe = secure_filename(filename)
    timestamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    return f"{timestamp}-{safe}" if safe else f"{timestamp}-upload"

# --- Routes ---

# Health check for Gradescope
@app.get("/api/v1/health")
def health():
    return jsonify({"ok": True, "status": "healthy"}), 200

# Upload endpoint
@app.post("/api/v1/upload")
def upload():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "error": "No file selected"}), 400

    # Only accept image types
    if not file.content_type.startswith("image/"):
        return jsonify({"ok": False, "error": "Only image files are allowed"}), 400

    blob_name = _make_blob_name(file.filename)
    blob_client = container_client.get_blob_client(blob_name)

    try:
        blob_client.upload_blob(file.stream, overwrite=True, content_settings=_content_settings_for(file.filename))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    url = f"{container_client.url}/{blob_name}"  # public-read container URL
    return jsonify({"ok": True, "url": url}), 200

# Gallery endpoint
@app.get("/api/v1/gallery")
def gallery():
    urls = []
    try:
        for blob in container_client.list_blobs():
            urls.append(f"{container_client.url}/{blob.name}")
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True, "gallery": urls}), 200

# Optional front-end
@app.get("/")
def index():
    return render_template("index.html")  # make sure your index.html is in templates/

# --- Run locally ---
if __name__ == "__main__":
    app.run(debug=True)

