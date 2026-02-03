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
        print(f"\n[DEBUG] Starting analysis...")
        print(f"[DEBUG] Upload dir: {upload_dir}")
        print(f"[DEBUG] Output dir: {output_dir}")
        print(f"[DEBUG] Files: {saved_files}")

        config_path = PROJECT_ROOT / 'config' / 'model_params.yaml'
        print(f"[DEBUG] Config: {config_path}")

        run_analysis(upload_dir, output_dir, config_path)

        print(f"[DEBUG] Analysis complete!")
        print(f"[DEBUG] Output files:")
        for f in output_dir.glob('*'):
            print(f"  - {f.name}: {f.stat().st_size} bytes")

        return jsonify({
            'success': True,
            'message': f'Processed {len(saved_files)} files',
            'files': saved_files
        })

    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}")
        import traceback
        traceback.print_exc()
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


def find_free_port():
    """Find an available port between 5000-5010."""
    import socket
    for port in range(5000, 5011):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    raise RuntimeError("No free ports available (tried 5000-5010)")


def open_browser(port):
    """Open browser after short delay."""
    webbrowser.open(f'http://127.0.0.1:{port}')


def main():
    """Run Flask app and open browser."""
    # Find available port automatically
    port = find_free_port()

    print("=" * 60)
    print("DVH Analysis Tool")
    print("=" * 60)
    print("\nStarting server...")
    print(f"Opening browser at http://127.0.0.1:{port}")
    print("\nPress Ctrl+C to stop server")
    print("=" * 60)

    # Open browser after 1 second
    Timer(1, lambda: open_browser(port)).start()

    # Run Flask app on auto-detected port
    app.run(host='127.0.0.1', port=port, debug=False)


if __name__ == '__main__':
    main()
