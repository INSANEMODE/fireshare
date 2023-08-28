import json
import os, re, string
import shutil
import random
import logging
from subprocess import Popen
from textwrap import indent
from flask import Blueprint, render_template, request, Response, jsonify, current_app, send_file, redirect
from flask_login import current_user, login_required
from flask_cors import CORS
from sqlalchemy.sql import text
from pathlib import Path
from werkzeug.utils import secure_filename
import subprocess
from datetime import datetime
import uuid

from .constants import SUPPORTED_FILE_EXTENSIONS


from . import db
from .models import Video, VideoInfo, VideoView
from .constants import SUPPORTED_FILE_TYPES, SUPPORTED_FILE_EXTENSIONS

templates_path = os.environ.get('TEMPLATE_PATH') or 'templates'
api = Blueprint('api', __name__, template_folder=templates_path)

CORS(api, supports_credentials=True)

def run_ffmpeg_with_progress(input_path, output_path, progress_callback=None):
    paths = current_app.config['PATHS']
    progress_file_name = f"{paths['data']}/progress_{uuid.uuid4().hex}.txt"  # Generate a random progress file name
    command = [
        "ffmpeg",
        "-y",  # Overwrite output file if it already exists
        "-i", input_path,
        "-progress", progress_file_name,  # Output progress information to a file
        output_path
    ]

    # Run FFmpeg command
    process = subprocess.Popen(command, stderr=subprocess.PIPE)
    
    # Read the progress file and extract the progress value
    while process.poll() is None:
        if os.path.exists(progress_file_name):
            with open(progress_file_name, "r") as progress_file:
                progress_data = progress_file.read()
                progress = re.findall(r"progress=([\d.]+)", progress_data)
                if progress:
                    progress_percentage = float(progress[0])  # Convert progress to float
                    if progress_callback:
                        progress_callback(progress_percentage)

    # Clean up progress file
    subprocess.run(["rm", progress_file_name])

    # Check the exit code of the process
    if process.returncode != 0:
        raise Exception("FFmpeg conversion failed")

# Example callback function
def update_upload_progress(progress):
    # Update the upload card with the progress percentage
    print(f"Conversion progress: {progress:.2f}%", flush=True)


def get_video_path(id, subid=None):
    video = Video.query.filter_by(video_id=id).first()
    if not video:
        raise Exception(f"No video found for {id}")
    paths = current_app.config['PATHS']
    subid_suffix = f"-{subid}" if subid else ""
    ext = ".mp4" if subid else video.extension
    video_path = paths["processed"] / "video_links" / f"{id}{subid_suffix}{ext}"
    return str(video_path)

@api.route('/w/<video_id>')
def video_metadata(video_id):
    video = Video.query.filter_by(video_id=video_id).first()
    if video:
        return render_template('metadata.html', video=video.json())
    else:
        return redirect('/#/w/{}'.format(video_id), code=302)

@api.route('/api/config')
def config():
    paths = current_app.config['PATHS']
    config_path = paths['data'] / 'config.json'
    file = open(config_path)
    config = json.load(file)
    file.close()
    if config_path.exists():
        return config["ui_config"]
    else:
        return jsonify({})

@api.route('/api/admin/config', methods=["GET", "PUT"])
@login_required
def get_or_update_config():
    paths = current_app.config['PATHS']
    if request.method == 'GET':
        config_path = paths['data'] / 'config.json'
        file = open(config_path)
        config = json.load(file)
        file.close()
        if config_path.exists():
            return config
        else:
            return jsonify({})
    if request.method == 'PUT':
        config = request.json["config"]
        config_path = paths['data'] / 'config.json'
        if not config:
            return Response(status=400, response='A config must be provided.')
        if not config_path.exists():
            return Response(status=500, response='Could not find a config to update.')
        config_path.write_text(json.dumps(config, indent=2))
        return Response(status=200)

@api.route('/api/admin/warnings', methods=["GET"])
@login_required
def get_warnings():
    warnings = current_app.config['WARNINGS']
    if request.method == 'GET':
        if len(warnings) == 0:
            return jsonify({})
        else:
            return jsonify(warnings)

@api.route('/api/manual/scan')
@login_required
def manual_scan():
    if not current_app.config["ENVIRONMENT"] == 'production':
        return Response(response='You must be running in production for this task to work.', status=400)
    else:
        current_app.logger.info(f"Executed manual scan")
        Popen("fireshare bulk-import", shell=True)
    return Response(status=200)

@api.route('/api/videos')
@login_required
def get_videos():
    sort = request.args.get('sort')
    if "views" in sort:
        videos = Video.query.join(VideoInfo).all()
    else:
        videos = Video.query.join(VideoInfo).order_by(text(sort)).all()

    videos_json = []
    for v in videos:
        vjson = v.json()
        vjson["view_count"] = VideoView.count(v.video_id)
        videos_json.append(vjson)

    if sort == "views asc":
        videos_json = sorted(videos_json, key=lambda d: d['view_count'])
    if sort == 'views desc':
        videos_json = sorted(videos_json, key=lambda d: d['view_count'], reverse=True)

    return jsonify({"videos": videos_json})

@api.route('/api/video/random')
@login_required
def get_random_video():
    row_count = Video.query.count()
    random_video = Video.query.offset(int(row_count * random.random())).first()
    current_app.logger.info(f"Fetched random video {random_video.video_id}: {random_video.info.title}")
    return jsonify(random_video.json())

@api.route('/api/video/public/random')
def get_random_public_video():
    row_count =  Video.query.filter(Video.info.has(private=False)).filter_by(available=True).count()
    random_video = Video.query.filter(Video.info.has(private=False)).filter_by(available=True).offset(int(row_count * random.random())).first()
    current_app.logger.info(f"Fetched public random video {random_video.video_id}: {random_video.info.title}")
    return jsonify(random_video.json())

@api.route('/api/videos/public')
def get_public_videos():
    sort = request.args.get('sort')
    if "views" in sort:
        videos = Video.query.join(VideoInfo).filter_by(private=False)
    else:
        videos = Video.query.join(VideoInfo).filter_by(private=False).order_by(text(sort))
    
    videos_json = []
    for v in videos:
        vjson = v.json()
        if (not vjson["available"]):
            continue
        vjson["view_count"] = VideoView.count(v.video_id)
        videos_json.append(vjson)

    if sort == "views asc":
        videos_json = sorted(videos_json, key=lambda d: d['view_count'])
    if sort == 'views desc':
        videos_json = sorted(videos_json, key=lambda d: d['view_count'], reverse=True)

    return jsonify({"videos": videos_json})

@api.route('/api/video/delete/<id>', methods=["DELETE"])
@login_required
def delete_video(id):
    video = Video.query.filter_by(video_id=id).first()
    if video:
        logging.info(f"Deleting video: {video.video_id}")
        VideoInfo.query.filter_by(video_id=id).delete()
        Video.query.filter_by(video_id=id).delete()
        db.session.commit()
        file_path = f"{current_app.config['VIDEO_DIRECTORY']}/{video.path}"
        link_path = f"{current_app.config['PROCESSED_DIRECTORY']}/video_links/{id}.{video.extension}"
        derived_path = f"{current_app.config['PROCESSED_DIRECTORY']}/derived/{id}"
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(link_path):
                os.remove(link_path)
            if os.path.exists(derived_path):
                shutil.rmtree(derived_path)
        except OSError as e:
            logging.error(f"Error deleting: {e.strerror}")
        return Response(status=200)
        
    else:
        return Response(status=404, response=f"A video with id: {id}, does not exist.")

@api.route('/api/video/details/<id>', methods=["GET", "PUT"])
def handle_video_details(id):
    if request.method == 'GET':
        # db lookup and get the details title/views/etc
        # video_id = request.args['id']
        video = Video.query.filter_by(video_id=id).first()
        if video:
            return jsonify(video.json())
        else:
            return jsonify({
                'message': 'Video not found'
            }), 404
    if request.method == 'PUT':
        if not current_user.is_authenticated:
            return Response(response='You do not have access to this resource.', status=401)
        video_info = VideoInfo.query.filter_by(video_id=id).first()
        if video_info:
            db.session.query(VideoInfo).filter_by(video_id=id).update(request.json)
            db.session.commit()
            return Response(status=201)
        else:
            return jsonify({
                'message': 'Video details not found'
            }), 404

@api.route('/api/video/poster', methods=['GET'])
def get_video_poster():
    video_id = request.args['id']
    webm_poster_path = Path(current_app.config["PROCESSED_DIRECTORY"], "derived", video_id, "boomerang-preview.webm")
    jpg_poster_path = Path(current_app.config["PROCESSED_DIRECTORY"], "derived", video_id, "poster.jpg")
    if request.args.get('animated'):
        return send_file(webm_poster_path, mimetype='video/webm')
    else:
        return send_file(jpg_poster_path, mimetype='image/jpg')

@api.route('/api/video/view', methods=['POST'])
def add_video_view():
    video_id = request.json['video_id']
    if request.headers.getlist("X-Forwarded-For"):
        ip_address = request.headers.getlist("X-Forwarded-For")[0].split(",")[0]
    else:
        ip_address = request.remote_addr
    VideoView.add_view(video_id, ip_address)
    return Response(status=200)

@api.route('/api/video/<video_id>/views', methods=['GET'])
def get_video_views(video_id):
    views = VideoView.count(video_id)
    return str(views)

@api.route('/api/upload/public', methods=['POST'])
def public_upload_video():
    paths = current_app.config['PATHS']
    with open(paths['data'] / 'config.json', 'r') as configfile:
        try:
            config = json.load(configfile)
        except:
            logging.error("Invalid or corrupt config file")
            return Response(status=400)
        configfile.close()
        
    if not config['app_config']['allow_public_upload']:
        logging.warn("A public upload attempt was made but public uploading is disabled")
        return Response(status=401)
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400


     
    upload_token = request.form.get("uploadToken")
    chunk_number = int(request.form.get("chunkNumber"))
    total_chunks = int(request.form.get("totalChunks"))
    OGFileName = request.form.get("OGFileName")
    print(f"OGFileName: {OGFileName}", flush=True)
    print(f"filename: {file.filename}", flush=True)
    filename = secure_filename(file.filename)
    print(f"secure filename: {filename}", flush=True)
    name_no_type = Path(filename).stem
    og_name_no_type = Path(OGFileName).stem
    print(f"name_no_type: {name_no_type}", flush=True)
    file_extension = Path(filename).suffix
    og_file_extension = Path(OGFileName).suffix

    if f".{og_file_extension}".lower() not in SUPPORTED_FILE_EXTENSIONS:
        return jsonify({"error": "Unsupported Media Type"}), 415
    if f"{file.mimetype}".lower() not in SUPPORTED_FILE_TYPES:
        return jsonify({"error": "Unsupported Media Type"}), 415
    upload_directory = paths['video'] / config['app_config']['public_upload_folder_name']
    if not os.path.exists(upload_directory):
        os.makedirs(upload_directory)
    save_path = os.path.join(upload_directory, upload_token)

    # Save the uploaded chunk
    chunk_path = f"{save_path}_{chunk_number}"
    file.save(chunk_path)

    # Check if all chunks have been uploaded
    if chunk_number == total_chunks - 1:
        # Merge the chunks into a single MP4 file
        merged_filename = secure_filename(OGFileName)
        merged_path = os.path.join(upload_directory, merged_filename)
        if os.path.exists(merged_path):
            current_datetime = datetime.now().strftime("%H-%M-%S")
            str_current_datetime = str(current_datetime)
            merged_path = os.path.join(upload_directory, f"{str_current_datetime}-{merged_filename}")
        with open(merged_path, "ab") as merged_file:
            for i in range(total_chunks):
                chunk_path = f"{save_path}_{i}"
                with open(chunk_path, "rb") as chunk_file:
                    merged_file.write(chunk_file.read())
                os.remove(chunk_path)

        # Optional: Convert the merged file to a different format if needed
        if og_file_extension != "mp4":

            converted_path = os.path.join(upload_directory, f"{og_name_no_type}.mp4")
            if os.path.exists(converted_path):
                current_datetime = datetime.now().strftime("%H-%M-%S")
                str_current_datetime = str(current_datetime)
                converted_path = os.path.join(upload_directory, f"{og_name_no_type}-{str_current_datetime}.mp4")
            print(f"converted_path: {converted_path}", flush=True)
            run_ffmpeg_with_progress(merged_path, converted_path, progress_callback=update_upload_progress)
            os.remove(merged_path)
            merged_path = converted_path
        manual_scan()
        return jsonify({"message": "File uploaded successfully", "file_path": merged_path}), 200
    else:
        return jsonify({"message": "Chunk uploaded successfully"}), 200


@api.route('/api/upload', methods=['POST'])
@login_required
def upload_video():
    paths = current_app.config['PATHS']
    with open(paths['data'] / 'config.json', 'r') as configfile:
        try:
            config = json.load(configfile)
        except:
            return Response(status=500, response="Invalid or corrupt config file")
        configfile.close()
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    upload_token = request.form.get("uploadToken")
    chunk_number = int(request.form.get("chunkNumber"))
    total_chunks = int(request.form.get("totalChunks"))
    OGFileName = request.form.get("OGFileName")
    print(f"OGFileName: {OGFileName}", flush=True)
    print(f"filename: {file.filename}", flush=True)
    filename = secure_filename(file.filename)
    print(f"secure filename: {filename}", flush=True)
    name_no_type = Path(filename).stem
    og_name_no_type = Path(OGFileName).stem
    print(f"name_no_type: {name_no_type}", flush=True)
    file_extension = Path(filename).suffix
    og_file_extension = Path(OGFileName).suffix
    if f".{og_file_extension}".lower() not in SUPPORTED_FILE_EXTENSIONS:
        return jsonify({"error": f"Unsupported Media Type: .{og_file_extension}"}), 415
    if f"{file.mimetype}".lower() not in SUPPORTED_FILE_TYPES:
        return jsonify({"error": f"Unsupported Media Type: {file.mimetype}"}), 415
    upload_directory = paths['video'] / config['app_config']['admin_upload_folder_name']
    if not os.path.exists(upload_directory):
        os.makedirs(upload_directory)
    save_path = os.path.join(upload_directory, upload_token)

    # Save the uploaded chunk
    chunk_path = f"{save_path}_{chunk_number}"
    file.save(chunk_path)

    # Check if all chunks have been uploaded
    if chunk_number == total_chunks - 1:
        # Merge the chunks into a single MP4 file
        merged_filename = secure_filename(OGFileName)
        merged_path = os.path.join(upload_directory, merged_filename)
        if os.path.exists(merged_path):
            current_datetime = datetime.now().strftime("%H-%M-%S")
            str_current_datetime = str(current_datetime)
            merged_path = os.path.join(upload_directory, f"{str_current_datetime}-{merged_filename}")
        with open(merged_path, "ab") as merged_file:
            for i in range(total_chunks):
                chunk_path = f"{save_path}_{i}"
                with open(chunk_path, "rb") as chunk_file:
                    merged_file.write(chunk_file.read())
                os.remove(chunk_path)

        # Optional: Convert the merged file to a different format if needed
        if og_file_extension != "mp4":

            converted_path = os.path.join(upload_directory, f"{og_name_no_type}.mp4")
            if os.path.exists(converted_path):
                current_datetime = datetime.now().strftime("%H-%M-%S")
                str_current_datetime = str(current_datetime)
                converted_path = os.path.join(upload_directory, f"{og_name_no_type}-{str_current_datetime}.mp4")
            print(f"converted_path: {converted_path}", flush=True)
            run_ffmpeg_with_progress(merged_path, converted_path, progress_callback=update_upload_progress)
            os.remove(merged_path)
            merged_path = converted_path
        manual_scan()
        return jsonify({"message": "File uploaded successfully", "file_path": merged_path}), 200
    else:
        return jsonify({"message": "Chunk uploaded successfully"}), 200

@api.route('/api/video')
def get_video():
    video_id = request.args.get('id')
    subid = request.args.get('subid')
    video_path = get_video_path(video_id, subid)
    file_size = os.stat(video_path).st_size
    start = 0
    length = 10240

    range_header = request.headers.get('Range', None)
    if range_header:
        m = re.search('([0-9]+)-([0-9]*)', range_header)
        g = m.groups()
        byte1, byte2 = 0, None
        if g[0]:
            byte1 = int(g[0])
        if g[1]:
            byte2 = int(g[1])
        if byte1 < file_size:
            start = byte1
        if byte2:
            length = byte2 + 1 - byte1
        else:
            length = file_size - start

    with open(video_path, 'rb') as f:
        f.seek(start)
        chunk = f.read(length)

    rv = Response(chunk, 206, mimetype='video/mp4', content_type='video/mp4', direct_passthrough=True)
    rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(start, start + length - 1, file_size))
    return rv

@api.after_request
def after_request(response):
    response.headers.add('Accept-Ranges', 'bytes')
    return response
