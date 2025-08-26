import os
import threading
import uuid
import json
import subprocess
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads'))
app.config['RUNS_FOLDER'] = os.path.abspath(os.path.join(os.path.dirname(__file__), 'outputs'))
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RUNS_FOLDER'], exist_ok=True)


def launch_run(
    image_path: str,
    description: str,
    duration: int,
    num_videos: int,
    extract_frames_max: int,
    run_id: str,
    tail_image_path: str | None = None,
    kling_prompts_json: str | None = None,
):
    # Invoke the main agent synchronously (runs in background thread)
    cmd = [
        'python', 'main.py',
        '--image', image_path,
        '--description', description,
        '--duration', str(duration),
        '--num_videos', str(num_videos),
        '--extract_frames_max', str(extract_frames_max),
        '--run_id', run_id,
    ]
    if tail_image_path:
        cmd += ["--tail_image", tail_image_path]
    if kling_prompts_json:
        cmd += ["--kling_prompts_json", kling_prompts_json]
    subprocess.Popen(cmd, cwd=os.path.dirname(__file__))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    filename = secure_filename(image_file.filename)
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    image_file.save(image_path)

    description = request.form.get('description', '')
    duration = int(request.form.get('duration', '5'))
    num_videos = int(request.form.get('num_videos', '3'))
    extract_frames_max = int(request.form.get('extract_frames_max', '12'))

    # Optional tail image support
    tail_image_file = request.files.get('tail_image')
    tail_image_path = None
    if tail_image_file and getattr(tail_image_file, 'filename', ''):
        tail_filename = secure_filename(tail_image_file.filename)
        tail_image_path = os.path.join(app.config['UPLOAD_FOLDER'], tail_filename)
        tail_image_file.save(tail_image_path)

    # Optional per-video prompt overrides
    kling_prompts_json = request.form.get('kling_prompts_json', None)

    run_id = datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6]

    t = threading.Thread(
        target=launch_run,
        args=(image_path, description, duration, num_videos, extract_frames_max, run_id, tail_image_path, kling_prompts_json)
    )
    t.daemon = True
    t.start()

    return jsonify({'ok': True, 'run_id': run_id})


@app.route('/status/<run_id>')
def status(run_id: str):
    base = os.path.join(app.config['RUNS_FOLDER'], run_id)
    lineage_path = os.path.join(base, 'lineage.json')
    notes_path = os.path.join(base, 'notes.txt')
    status = {
        'exists': os.path.isdir(base),
        'lineage': None,
        'notes': None,
    }
    if os.path.exists(lineage_path):
        try:
            with open(lineage_path, 'r', encoding='utf-8') as f:
                status['lineage'] = json.load(f)
        except Exception:
            status['lineage'] = None
    if os.path.exists(notes_path):
        try:
            with open(notes_path, 'r', encoding='utf-8') as f:
                status['notes'] = f.read()
        except Exception:
            status['notes'] = None
    return jsonify(status)


@app.route('/runs')
def list_runs():
    runs = []
    base = app.config['RUNS_FOLDER']
    try:
        for name in os.listdir(base):
            run_dir = os.path.join(base, name)
            if not os.path.isdir(run_dir):
                continue
            lineage_path = os.path.join(run_dir, 'lineage.json')
            notes_path = os.path.join(run_dir, 'notes.txt')
            if os.path.exists(lineage_path) and os.path.exists(notes_path):
                mtime = max(os.path.getmtime(lineage_path), os.path.getmtime(notes_path))
                runs.append({
                    'id': name,
                    'mtime': mtime,
                })
        runs.sort(key=lambda r: r['mtime'], reverse=True)
    except Exception:
        runs = []
    return jsonify({'runs': runs})


@app.route('/moves')
def moves():
    # Return available moves and a scene suggestion for the given description
    try:
        from tools.camera_planner import INDOOR_MOVES, OUTDOOR_MOVES, detect_scene_type
    except Exception:
        INDOOR_MOVES, OUTDOOR_MOVES, detect_scene_type = [], [], lambda d: 'indoor'

    description = request.args.get('description', '')
    scene = detect_scene_type(description) if description else 'indoor'
    return jsonify({
        'scene': scene,
        'indoor_moves': INDOOR_MOVES,
        'outdoor_moves': OUTDOOR_MOVES,
    })


@app.route('/outputs/<path:subpath>')
def outputs_static(subpath: str):
    return send_from_directory(app.config['RUNS_FOLDER'], subpath)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)


