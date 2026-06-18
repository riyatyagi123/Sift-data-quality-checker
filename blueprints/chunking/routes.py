import os
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, current_app, send_from_directory
from services.chunker import split_csv

chunking_bp = Blueprint('chunking', __name__)

@chunking_bp.route('/chunk', methods=['GET'])
def chunk_page():
    # Verify that a cleaned file is ready, otherwise redirect to clean page
    cleaned_filepath = session.get('cleaned_filepath')
    if not cleaned_filepath or not os.path.exists(cleaned_filepath):
        return redirect(url_for('cleaning.clean_page'))
        
    metadata = session.get('csv_metadata', {})
    results = session.get('chunking_results')
    
    return render_template(
        'chunk.html',
        filename=metadata.get('filename', 'Unknown File'),
        results=results
    )

@chunking_bp.route('/chunk/generate', methods=['POST'])
def generate_chunks():
    cleaned_filepath = session.get('cleaned_filepath')
    if not cleaned_filepath or not os.path.exists(cleaned_filepath):
        return jsonify({'error': 'Cleaned file not found on server'}), 400
        
    try:
        # Get chunk size from POST request parameters
        data = request.get_json() or {}
        chunk_size_str = data.get('chunk_size') or request.form.get('chunk_size', '1000')
        
        try:
            chunk_size = int(chunk_size_str)
            if chunk_size <= 0:
                raise ValueError()
        except ValueError:
            return jsonify({'error': 'Invalid chunk size. Must be a positive integer.'}), 400
            
        # Create output subdirectory inside CHUNKS_FOLDER for this session to isolate chunk files
        session_id = session.get('session_id', 'default')
        output_dir = os.path.join(current_app.config['CHUNKS_FOLDER'], session_id)
        
        # Split CSV into chunks
        results = split_csv(cleaned_filepath, chunk_size, output_dir)
        
        if results['success']:
            # Save chunking results to session
            session['chunking_results'] = {
                'chunk_count': results['chunk_count'],
                'chunk_files': results['chunk_files'],
                'zip_filename': results['zip_filename'],
                'zip_dir': output_dir
            }
            return jsonify({
                'success': True,
                'chunk_count': results['chunk_count'],
                'chunk_files': results['chunk_files']
            })
        else:
            return jsonify({'error': results.get('error', 'Failed to generate chunks')}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chunking_bp.route('/download/chunks', methods=['GET'])
def download_chunks():
    chunk_meta = session.get('chunking_results')
    if not chunk_meta:
        return "No chunks generated in this session.", 404
        
    zip_dir = chunk_meta.get('zip_dir')
    zip_filename = chunk_meta.get('zip_filename')
    
    if not zip_dir or not zip_filename:
        return "Chunk archive details not found.", 404
        
    full_path = os.path.join(zip_dir, zip_filename)
    if not os.path.exists(full_path):
        return "Chunks zip archive not found on disk.", 404
        
    # secure serving with path traversal prevention built-in to send_from_directory
    return send_from_directory(
        directory=zip_dir,
        path=zip_filename,
        as_attachment=True,
        download_name=zip_filename
    )
