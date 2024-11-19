import os
import instaloader
import zipfile
import shutil
from flask import Flask, request, send_file, render_template, jsonify
from threading import Thread
import time

# Directory to store downloaded images
DOWNLOAD_DIR = "/tmp/downloads"  # Use /tmp for temporary file storage
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

app = Flask(__name__)

# Helper function for cleanup
def cleanup(zip_filepath):
    try:
        time.sleep(2)  # Allow time for file download to complete
        os.remove(zip_filepath)  # Remove the zip file
        shutil.rmtree(DOWNLOAD_DIR)  # Remove the downloads folder
    except Exception as cleanup_error:
        print(f"Error during cleanup: {cleanup_error}")

# Function to download images and create the zip file
def download_images(url):
    try:
        # Initialize Instaloader
        loader = instaloader.Instaloader()

        # Extract the shortcode from the URL
        shortcode = url.split('/')[-2]

        # Fetch the post using the shortcode
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        # Download the images directly into the 'downloads' folder
        loader.download_post(post, target=DOWNLOAD_DIR)

        # Create a ZIP file containing all the downloaded image files
        zip_filename = f"{shortcode}.zip"
        zip_filepath = os.path.join(DOWNLOAD_DIR, zip_filename)

        # Create the ZIP file
        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for root, dirs, files in os.walk(DOWNLOAD_DIR):
                for file in files:
                    if file.endswith('.jpg') or file.endswith('.png'):  # Only include image files
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, arcname=os.path.relpath(file_path, DOWNLOAD_DIR))

        # Start cleanup in a background thread to avoid blocking
        cleanup_thread = Thread(target=cleanup, args=(zip_filepath,))
        cleanup_thread.start()

        return zip_filepath  # Return the path to the ZIP file

    except Exception as e:
        return str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    zip_filepath = download_images(url)

    if zip_filepath.endswith('.zip'):
        return send_file(zip_filepath, as_attachment=True)
    else:
        return jsonify({"error": zip_filepath}), 500

if __name__ == '__main__':
    # Use 'host="0.0.0.0"' for Render
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
