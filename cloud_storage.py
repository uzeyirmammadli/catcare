from google.cloud import storage
import os

def upload_blob(source_file_path, destination_blob_name):
    """Uploads a file to Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket('your-bucket-name')
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)