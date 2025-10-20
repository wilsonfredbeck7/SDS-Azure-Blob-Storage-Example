
# Flask + Azure Blob Storage (Connection String) — Simple Uploader

This example demonstrates a tiny Flask app that lets users upload datasets (any file) to Azure Blob Storage using an **account connection string**.

## Quick start

1. **Python 3.10+** recommended. Create and activate a virtualenv.
2. Install deps:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env
   # then edit .env to set AZURE_STORAGE_CONNECTION_STRING
   ```
4. Run:
   ```bash
   flask --app app.py run --debug
   ```
5. Open http://127.0.0.1:5000 and upload a file.
6. Uploaded files appear in your Azure container (default: `datasets`). A simple file list is shown at `/files`.

## Notes

- Uses `BlobServiceClient.from_connection_string(...)`.
- Automatically creates the container if it doesn't exist.
- Filenames are sanitized and optionally prefixed with a timestamp to avoid collisions.
- For large files, `upload_blob` streams from the request without loading the whole file into memory.
- Set a max upload size with `MAX_CONTENT_LENGTH` (default 512 MB here).
- For production, consider Azure-managed identities or user-delegation SAS instead of a raw connection string.
