import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def get_file_size_kb(filepath: str) -> float:
    """Returns file size in KB."""
    try:
        size_bytes = os.path.getsize(filepath)
        return round(size_bytes / 1024, 1)
    except Exception as e:
        logger.error(f"Error getting file size: {e}")
        return 0.0

def parse_csv_metadata(filepath: str) -> dict:
    """
    Parses a CSV file to extract row count, column count, list of columns,
    and the first 10 rows for preview. Uses chunking to be memory efficient.
    """
    try:
        # Determine columns and row count using chunksize for memory efficiency
        total_rows = 0
        columns = []
        chunksize = 50000
        
        # Read file in chunks to get total count and columns
        for chunk in pd.read_csv(filepath, chunksize=chunksize, dtype=str):
            total_rows += len(chunk)
            if not columns:
                columns = list(chunk.columns)
                
        # Read first 10 rows for preview
        df_preview = pd.read_csv(filepath, nrows=10, dtype=str)
        # Fill NaN values with empty strings for JSON/frontend safety
        df_preview = df_preview.fillna('')
        
        preview_data = {
            'headers': list(df_preview.columns),
            'rows': df_preview.values.tolist()
        }
        
        return {
            'filename': os.path.basename(filepath),
            'rows': total_rows,
            'columns': len(columns),
            'column_names': columns,
            'filesize_kb': get_file_size_kb(filepath),
            'preview': preview_data
        }
    except Exception as e:
        logger.error(f"Error parsing CSV file {filepath}: {e}")
        raise ValueError(f"Failed to parse CSV file: {str(e)}")
