import os
import shutil
import tempfile
import zipfile
import uuid
import requests
from flask import Flask, render_template, request, send_file
import instaloader
import re

app = Flask(__name__)

def sanitize_filename(filename):
    """Create a safe filename by removing invalid characters."""
    return re.sub(r'[^\w\-_\. ]', '_', filename)

def download_instagram_post(post_url):
    """
    Download images from an Instagram post
    Returns:
    - Temporary directory path with downloaded images
    - List of downloaded filenames
    """
    L = instaloader.Instaloader(
        download_pictures=True,
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False
    )
    
    # Extract shortcode from URL
    shortcode = post_url.split('/')[-2] if 'instagram.com/p/' in post_url else post_url
    
    # Temporary directory for this download session
    temp_dir = tempfile.mkdtemp(prefix='insta_download_')
    
    try:
        # Get the post
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Track downloaded filenames
        downloaded_files = []
        
        # Check if it's a multi-image post
        if post.typename == 'GraphSidecar':
            # Download multiple images/videos
            for i, item in enumerate(post.get_sidecar_nodes()):
                # Determine file extension
                ext = 'mp4' if item.is_video else 'jpg'
                
                # Create unique filename
                filename = sanitize_filename(f'{shortcode}_{i+1}.{ext}')
                filepath = os.path.join(temp_dir, filename)
                
                # Download image or video
                if item.is_video:
                    # Use display_url for thumbnail, video_url for actual video
                    image_url = item.display_url
                    video_url = item.video_url
                    
                    # Download video
                    response = requests.get(video_url)
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                else:
                    # Use display_url for images
                    image_url = item.display_url
                    response = requests.get(image_url)
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                
                downloaded_files.append(filename)
        else:
            # Single image/video post
            ext = 'mp4' if post.is_video else 'jpg'
            filename = sanitize_filename(f'{shortcode}.{ext}')
            filepath = os.path.join(temp_dir, filename)
            
            # Download image or video
            if post.is_video:
                # Use display_url for thumbnail, video_url for actual video
                image_url = post.display_url
                video_url = post.video_url
                response = requests.get(video_url)
            else:
                # Use display_url for images
                image_url = post.display_url
                response = requests.get(image_url)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            downloaded_files.append(filename)
        
        return temp_dir, downloaded_files
    
    except Exception as e:
        # Clean up temporary directory if download fails
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_images():
    post_url = request.form.get('post_url')
    
    try:
        # Download images
        temp_dir, downloaded_files = download_instagram_post(post_url)
        
        # Create a zip file
        zip_filename = f'instagram_download_{uuid.uuid4().hex}.zip'
        zip_path = os.path.join(tempfile.gettempdir(), zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in downloaded_files:
                zipf.write(os.path.join(temp_dir, filename), filename)
        
        # Clean up temporary download directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Send zip file for download
        return send_file(
            zip_path, 
            as_attachment=True, 
            download_name=zip_filename,
            mimetype='application/zip'
        )
    
    except Exception as e:
        return str(e), 400

if __name__ == '__main__':
    app.run(debug=True)
