"""
Simple Flask web application for DVH analysis.
Runs locally on localhost, allows file upload and result download.
"""

import os
import sys
import webbrowser
from pathlib import Path
from threading import Timer
from flask import Flask, render_template, request, send_file, jsonify
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.runner import run_analysis


app = Flask(__name__)

# Get absolute paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent
app.config['UPLOAD_FOLDER'] = PROJECT_ROOT / 'web' / 'uploads'
app.config['OUTPUT_FOLDER'] = PROJECT_ROOT / 'web' / 'output'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file upload and process DVH files."""
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400

    files = request.files.getlist('files[]')

    if not files or files[0].filename == '':
        return jsonify({'error': 'No files selected'}), 400

    # Create temporary directories
    upload_dir = app.config['UPLOAD_FOLDER']
    output_dir = app.config['OUTPUT_FOLDER']
    upload_dir.mkdir(exist_ok=True, parents=True)
    output_dir.mkdir(exist_ok=True, parents=True)

    # Clear previous uploads
    for f in upload_dir.glob('*'):
        f.unlink()
    for f in output_dir.glob('*'):
        f.unlink()

    # Save uploaded files
    saved_files = []
    for file in files:
        if file.filename.endswith('.txt'):
            filepath = upload_dir / file.filename
            file.save(filepath)
            saved_files.append(file.filename)

    if not saved_files:
        return jsonify({'error': 'No valid DVH files (.txt) found'}), 400

    # Run analysis
    try:
        config_path = PROJECT_ROOT / 'config' / 'model_params.yaml'
        run_analysis(upload_dir, output_dir, config_path)

        return jsonify({
            'success': True,
            'message': f'Processed {len(saved_files)} files',
            'files': saved_files
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download/<filename>')
def download_file(filename):
    """Download result file (JSON or CSV)."""
    output_dir = app.config['OUTPUT_FOLDER']
    filepath = output_dir / filename

    if not filepath.exists():
        return jsonify({'error': 'File not found'}), 404

    return send_file(filepath, as_attachment=True)


@app.route('/results')
def get_results():
    """Get list of available result files."""
    output_dir = app.config['OUTPUT_FOLDER']

    if not output_dir.exists():
        return jsonify({'files': []})

    files = [
        {'name': f.name, 'size': f.stat().st_size}
        for f in output_dir.glob('*')
        if f.is_file()
    ]

    return jsonify({'files': files})


def open_browser():
    """Open browser after short delay."""
    webbrowser.open('http://127.0.0.1:5000')


def main():
    """Run Flask app and open browser."""
    print("=" * 60)
    print("DVH Analysis Tool")
    print("=" * 60)
    print("\nStarting server...")
    print("Opening browser at http://127.0.0.1:5000")
    print("\nPress Ctrl+C to stop server")
    print("=" * 60)

    # Open browser after 1 second
    Timer(1, open_browser).start()

    # Run Flask app
    app.run(host='127.0.0.1', port=5000, debug=False)


if __name__ == '__main__':
    main()
