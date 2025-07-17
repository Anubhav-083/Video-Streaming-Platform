"""
Video Streaming Platform using Flask, FFmpeg, and AWS S3
Author: Anubhav Shukla
"""

from flask import Flask, render_template, request, redirect
import sqlite3
import os
import boto3
import subprocess
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = "static/uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# AWS S3 configuration (replace with your actual credentials)
AWS_ACCESS_KEY = "YOUR_AWS_ACCESS_KEY"
AWS_SECRET_KEY = "YOUR_AWS_SECRET_KEY"
BUCKET_NAME = "your-s3-bucket-name"
REGION = "ap-south-1"

s3 = boto3.client('s3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION
)

def init_db():
    conn = sqlite3.connect('database.db')
    conn.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            s3_url TEXT
        )
    """)
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, s3_url FROM videos")
    videos = cursor.fetchall()
    conn.close()
    return render_template("index.html", videos=videos)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        title = request.form['title']
        file = request.files['video']
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)

        # Convert video to MP4 using FFmpeg
        converted_filename = filename.rsplit('.', 1)[0] + ".mp4"
        converted_path = os.path.join(app.config['UPLOAD_FOLDER'], converted_filename)
        subprocess.run(["ffmpeg", "-i", input_path, converted_path])

        # Upload to S3
        s3.upload_file(converted_path, BUCKET_NAME, converted_filename)
        s3_url = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{converted_filename}"

        # Save metadata to DB
        conn = sqlite3.connect('database.db')
        conn.execute("INSERT INTO videos (title, s3_url) VALUES (?, ?)", (title, s3_url))
        conn.commit()
        conn.close()

        # Clean up local files
        os.remove(input_path)
        os.remove(converted_path)

        return redirect('/')
    return render_template("upload.html")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
