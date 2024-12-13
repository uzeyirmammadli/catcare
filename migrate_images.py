from google.cloud import storage
import os
from catcare import create_app, db
from catcare.models import Case

def upload_existing_images():
    # Initialize Cloud Storage client
    client = storage.Client()
    bucket = client.bucket('eco-layout-442118-t8-uploads')
    
    # Upload each file from your local uploads directory
    local_upload_dir = 'catcare/static/uploads'
    for filename in os.listdir(local_upload_dir):
        file_path = os.path.join(local_upload_dir, filename)
        blob = bucket.blob(filename)
        
        with open(file_path, 'rb') as f:
            blob.upload_from_file(f)
            
        print(f"Uploaded {filename}")

def update_image_urls():
    app = create_app()
    with app.app_context():
        cases = Case.query.all()
        for case in cases:
            if case.photo and not case.photo.startswith('https://'):
                # Get just the filename from the path
                filename = os.path.basename(case.photo)
                # Update to Cloud Storage URL
                case.photo = f"https://storage.googleapis.com/eco-layout-442118-t8-uploads/{filename}"
        db.session.commit()
        print("Updated database URLs")

if __name__ == '__main__':
    upload_existing_images()
    update_image_urls()