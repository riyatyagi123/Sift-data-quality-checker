import os
from flask import Blueprint, render_template, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from services.csv_parser import parse_csv_metadata

upload_bp = Blueprint('upload', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@upload_bp.route('/upload', methods=['GET'])
def upload_page():
    # Clear session values to start fresh on a new upload visit if query parameter resets it
    if request.args.get('reset') == '1':
        session.pop('csv_filepath', None)
        session.pop('csv_metadata', None)
        session.pop('validation_results', None)
        session.pop('cleaned_filepath', None)
        session.pop('cleaning_results', None)
        session.pop('chunking_results', None)
        
    return render_template('upload.html')

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only CSV files are supported'}), 400
        
    try:
        # Sanitize and save temporary file
        filename = secure_filename(file.filename)
        # Ensure name ends in .csv even after sanitizing
        if not filename.endswith('.csv'):
            filename += '.csv'
            
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Parse metadata using our memory-efficient parser
        metadata = parse_csv_metadata(filepath)
        
        # Save filepath and metadata into the session
        session['csv_filepath'] = filepath
        session['csv_metadata'] = metadata
        
        # Reset subsequent step cache
        session.pop('validation_results', None)
        session.pop('cleaned_filepath', None)
        session.pop('cleaning_results', None)
        session.pop('chunking_results', None)
        
        return jsonify({
            'success': True,
            'filename': metadata['filename'],
            'rows': metadata['rows'],
            'columns': metadata['columns'],
            'filesize_kb': metadata['filesize_kb'],
            'preview': metadata['preview']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
