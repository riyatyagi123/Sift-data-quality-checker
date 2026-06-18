import os
from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from services.validator import validate_csv

validation_bp = Blueprint('validation', __name__)

@validation_bp.route('/validate', methods=['GET'])
def validate_page():
    # If no file is in session, redirect to upload page
    filepath = session.get('csv_filepath')
    if not filepath or not os.path.exists(filepath):
        return redirect(url_for('upload.upload_page'))
        
    metadata = session.get('csv_metadata', {})
    results = session.get('validation_results')
    
    # Render page. If validation hasn't run, JS will hit /validate/run
    return render_template(
        'validate.html',
        filename=metadata.get('filename', 'Unknown File'),
        results=results
    )

@validation_bp.route('/validate/run', methods=['POST'])
def run_validation():
    filepath = session.get('csv_filepath')
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'No active session file found'}), 400
        
    try:
        # Run CSV validation checks
        results = validate_csv(filepath)
        
        # Cache results in the session
        session['validation_results'] = results
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
