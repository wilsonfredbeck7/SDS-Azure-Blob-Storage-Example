
import os
import mimetypes
import datetime as dt
from pathlib import Path
from typing import Optional

from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from azure.storage.blob import BlobServiceClient, ContentSettings

# Load environment variables from .env if present
load_dotenv()

# --- Config ---
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "datasets")
FILE_PREFIX = os.getenv("FILE_PREFIX", "").strip()
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
MAX_CONTENT_MB = int(os.getenv("MAX_CONTENT_MB", "512"))  # 512 MB default

if not AZURE_STORAGE_CONNECTION_STRING:
    raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is not set. Put it in .env or your environment.")

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_MB * 1024 * 1024  # enforce size limit

# Initialize Blob service and ensure container exists
bsc = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = bsc.get_container_client(CONTAINER_NAME)
try:
    container_client.create_container()
except Exception:
    # It's fine if it already exists
    pass

# --- Helpers ---
def _content_settings_for(filename: str) -> ContentSettings:
    ctype, _ = mimetypes.guess_type(filename)
    return ContentSettings(content_type=ctype or "application/octet-stream")

def _make_blob_name(filename: str) -> str:
    """Optionally prefix and timestamp the filename to avoid collisions."""
    safe = secure_filename(filename)
    timestamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    # Keep original name but prepend timestamp; add optional virtual folder prefix
    name = f"{timestamp}__{safe}" if safe else f"{timestamp}__upload"
    return f"{FILE_PREFIX}{name}" if FILE_PREFIX else name

# --- Routes ---
@app.get("/")
def index():
    return render_template("upload.html", container=CONTAINER_NAME)

@app.post("/upload")
def upload():
    if "file" not in request.files:
        flash("No file part in the request.", "error")
        return redirect(url_for("index"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("index"))

    blob_name = _make_blob_name(file.filename)
    blob_client = container_client.get_blob_client(blob_name)

    try:
        blob_client.upload_blob(
            file.stream,  # stream directly
            overwrite=False,
            content_settings=_content_settings_for(file.filename),
        )
    except Exception as e:
        # If name collision happens, try once with a unique suffix
        try:
            alt_name = _make_blob_name(f"dup_{file.filename}")
            container_client.get_blob_client(alt_name).upload_blob(
                file.stream,
                overwrite=False,
                content_settings=_content_settings_for(file.filename),
            )
            blob_name = alt_name
        except Exception as e2:
            flash(f"Upload failed: {e2}", "error")
            return redirect(url_for("index"))

    flash(f"Uploaded to blob '{blob_name}' in container '{CONTAINER_NAME}'.", "success")
    return redirect(url_for("files"))

@app.get("/files")
def files():
    blobs = []
    try:
        for blob in container_client.list_blobs(name_starts_with=FILE_PREFIX or None):
            blobs.append({
                "name": blob.name,
                "size": blob.size,
                "last_modified": blob.last_modified,
                "url": None,  # direct account URL requires known account/endpoint; usually you'd serve via SAS
            })
    except Exception as e:
        flash(f"Could not list blobs: {e}", "error")

    return render_template("files.html", blobs=blobs, container=CONTAINER_NAME, prefix=FILE_PREFIX)

# (Optional) Quick route to generate a short-lived read-only SAS URL for a blob
# Useful for sharing/previewing files. Requires account key in the connection string.
from azure.storage.blob import BlobSasPermissions, generate_blob_sas

@app.get("/sas/<path:blob_name>")
def sas_for_blob(blob_name: str):
    # Try to get account name/key from the client credential (works with connection string auth)
    try:
        account_name = container_client.account_name
        # Note: account_key is stored in the bsc.credential when using connection string
        account_key = getattr(getattr(bsc, "credential", None), "account_key", None)
        if not account_key:
            flash("No account key available to generate SAS (consider a different auth).", "error")
            return redirect(url_for("files"))

        expiry = dt.datetime.utcnow() + dt.timedelta(minutes=30)
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=CONTAINER_NAME,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
            start=dt.datetime.utcnow() - dt.timedelta(minutes=5),
        )
        base_url = f"https://{account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}"
        return redirect(f"{base_url}?{sas_token}")
    except Exception as e:
        flash(f"Failed to generate SAS: {e}", "error")
        return redirect(url_for("files"))

if __name__ == "__main__":
    app.run(debug=True)
