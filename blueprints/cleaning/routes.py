import os
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, current_app, send_from_directory, request
from services.cleaner import clean_csv

cleaning_bp = Blueprint('cleaning', __name__)

@cleaning_bp.route('/clean', methods=['GET'])
def clean_page():
    filepath = session.get('csv_filepath')
    if not filepath or not os.path.exists(filepath):
        return redirect(url_for('upload.upload_page'))
        
    metadata = session.get('csv_metadata', {})
    results = session.get('cleaning_results')
    
    return render_template(
        'cleaned.html',
        filename=metadata.get('filename', 'Unknown File'),
        results=results
    )

@cleaning_bp.route('/clean/run', methods=['POST'])
def run_cleaning():
    filepath = session.get('csv_filepath')
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'No active session file found'}), 400
        
    try:
        data = request.get_json() or {}
        mode = data.get('mode', 'SMART')
        if mode not in ['STRICT', 'SMART', 'SOFT']:
            mode = 'SMART'
            
        base_name = os.path.basename(filepath)
        name, ext = os.path.splitext(base_name)
        cleaned_filename = f"{name}_cleaned{ext}"
        removed_filename = f"{name}_removed{ext}"
        
        cleaned_filepath = os.path.join(current_app.config['PROCESSED_FOLDER'], cleaned_filename)
        removed_filepath = os.path.join(current_app.config['PROCESSED_FOLDER'], removed_filename)
        
        # Run clean_csv
        results = clean_csv(filepath, cleaned_filepath, removed_filepath, mode=mode)
        
        # Save output details in session - ONLY store the stats to avoid cookie size issues
        session['cleaned_filename'] = cleaned_filename
        session['cleaned_filepath'] = cleaned_filepath
        session['removed_filepath'] = removed_filepath
        session['cleaning_results'] = results['stats']
        session['cleaning_mode'] = mode
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cleaning_bp.route('/download/cleaned', methods=['GET'])
def download_cleaned():
    filename = session.get('cleaned_filename')
    if not filename:
        return "No cleaned file found in session.", 404
        
    folder = current_app.config['PROCESSED_FOLDER']
    full_path = os.path.join(folder, filename)
    if not os.path.exists(full_path):
        return "Cleaned file not found.", 404
        
    return send_from_directory(directory=folder, path=filename, as_attachment=True, download_name=filename)

@cleaning_bp.route('/download/errors', methods=['GET'])
def download_errors():
    filepath = session.get('csv_filepath')
    if not filepath:
        return "No active file in session.", 404
    base_name = os.path.basename(filepath)
    name, ext = os.path.splitext(base_name)
    filename = f"{name}_errors{ext}"
    folder = current_app.config['PROCESSED_FOLDER']
    full_path = os.path.join(folder, filename)
    if not os.path.exists(full_path):
        return "Errors file not found.", 404
    return send_from_directory(directory=folder, path=filename, as_attachment=True, download_name=filename)

@cleaning_bp.route('/download/warnings', methods=['GET'])
def download_warnings():
    filepath = session.get('csv_filepath')
    if not filepath:
        return "No active file in session.", 404
    base_name = os.path.basename(filepath)
    name, ext = os.path.splitext(base_name)
    filename = f"{name}_warnings{ext}"
    folder = current_app.config['PROCESSED_FOLDER']
    full_path = os.path.join(folder, filename)
    if not os.path.exists(full_path):
        return "Warnings file not found.", 404
    return send_from_directory(directory=folder, path=filename, as_attachment=True, download_name=filename)

@cleaning_bp.route('/download/duplicates', methods=['GET'])
def download_duplicates():
    filepath = session.get('csv_filepath')
    if not filepath:
        return "No active file in session.", 404
    base_name = os.path.basename(filepath)
    name, ext = os.path.splitext(base_name)
    filename = f"{name}_duplicates{ext}"
    folder = current_app.config['PROCESSED_FOLDER']
    full_path = os.path.join(folder, filename)
    if not os.path.exists(full_path):
        return "Duplicates file not found.", 404
    return send_from_directory(directory=folder, path=filename, as_attachment=True, download_name=filename)

@cleaning_bp.route('/download/audit', methods=['GET'])
def download_audit():
    filepath = session.get('csv_filepath')
    if not filepath:
        return "No active file in session.", 404
    base_name = os.path.basename(filepath)
    name, ext = os.path.splitext(base_name)
    filename = f"{name}_audit_report.json"
    folder = current_app.config['PROCESSED_FOLDER']
    full_path = os.path.join(folder, filename)
    if not os.path.exists(full_path):
        return "Audit report not found.", 404
    return send_from_directory(directory=folder, path=filename, as_attachment=True, download_name=filename)

@cleaning_bp.route('/download/removed_columns', methods=['GET'])
def download_removed_columns():
    filepath = session.get('csv_filepath')
    if not filepath:
        return "No active file in session.", 404
    base_name = os.path.basename(filepath)
    name, ext = os.path.splitext(base_name)
    filename = f"{name}_removed_columns.json"
    folder = current_app.config['PROCESSED_FOLDER']
    full_path = os.path.join(folder, filename)
    if not os.path.exists(full_path):
        return "Removed columns file not found.", 404
    return send_from_directory(directory=folder, path=filename, as_attachment=True, download_name=filename)
