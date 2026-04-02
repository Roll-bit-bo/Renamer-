import json
import logging
from typing import Dict, List, Union

def load_json_file(file_path) -> Union[Dict, List]:
    """Loads data from a JSON file, returning a dict or list."""
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Could not load file {file_path}: {e}")
    return [] if 'history' in file_path.name else {}

def save_json_file(file_path, data: Union[Dict, List]) -> bool:
    """Saves data to a JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logging.error(f"Failed to save to {file_path}: {e}")
        return False