import os
import zipfile
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def split_csv(input_filepath: str, chunk_size: int, output_dir: str) -> dict:
    """
    Splits the CSV file at input_filepath into chunks of chunk_size rows,
    preserves headers, and names them chunk_001.csv, chunk_002.csv, etc.
    Saves them inside output_dir and creates a zip file with all chunks.
    """
    try:
        # Clear output directory first if it exists, or create it
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        else:
            # Delete old csv files in output_dir
            for f in os.listdir(output_dir):
                if f.endswith('.csv') or f.endswith('.zip'):
                    try:
                        os.remove(os.path.join(output_dir, f))
                    except Exception as e:
                        logger.warning(f"Failed to delete old chunk file {f}: {e}")
                        
        # Read headers
        df_head = pd.read_csv(input_filepath, nrows=1)
        headers = list(df_head.columns)
        
        chunk_files = []
        chunk_idx = 1
        
        # Split using pandas chunksize reader
        for chunk in pd.read_csv(input_filepath, chunksize=chunk_size, dtype=str):
            chunk = chunk.fillna('')
            chunk_filename = f"chunk_{chunk_idx:03d}.csv"
            chunk_filepath = os.path.join(output_dir, chunk_filename)
            
            chunk.to_csv(chunk_filepath, index=False)
            chunk_files.append(chunk_filename)
            chunk_idx += 1
            
        # Create ZIP archive containing all chunks
        zip_filename = "chunks.zip"
        zip_filepath = os.path.join(output_dir, zip_filename)
        
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for chunk_file in chunk_files:
                file_path = os.path.join(output_dir, chunk_file)
                zipf.write(file_path, arcname=chunk_file)
                
        return {
            'success': True,
            'chunk_count': len(chunk_files),
            'chunk_files': chunk_files,
            'zip_filename': zip_filename,
            'zip_filepath': zip_filepath
        }
    except Exception as e:
        logger.error(f"Error splitting CSV file: {e}")
        return {
            'success': False,
            'error': str(e)
        }
