"""
Core Services Logic.
Handles the business logic for file manipulation, renaming algorithms, and analysis.
"""
import os
import logging
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Callable

import config

def generate_new_name(base_name: str, count: int, original_filename: str) -> str:
    """
    Generates a new filename based on the base_name pattern.
    Supports {original}, {num}, and {date} placeholders.
    Defaults to {base_name}_{count:03d}{ext} if no placeholders used.
    """
    path = Path(original_filename)
    ext = path.suffix
    stem = path.stem
    
    # Check for placeholders in the user provided pattern
    placeholders = ["{original}", "{num}", "{date}"]
    if any(p in base_name for p in placeholders):
        new_stem = base_name.replace("{original}", stem).replace("{num}", f"{count:03d}")
        
        # Replace {date} with modified time or current date
        if "{date}" in new_stem:
            try:
                mtime = path.stat().st_mtime
                date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
            except OSError:
                date_str = datetime.now().strftime('%Y-%m-%d')
            new_stem = new_stem.replace("{date}", date_str)
            
        return f"{new_stem}{ext}"
    
    # Default pattern if no placeholders are used
    return f"{base_name}_{count:03d}{ext}"

def get_target_files(folder_path: Path, file_type: str, contains_filter: str) -> Tuple[List[str], str | None]:
    """
    Scans a folder and filters files based on extension and text content.
    Returns: (list_of_filenames, error_message)
    """
    if not folder_path or not folder_path.is_dir():
        return [], "Folder not found or is not a directory."

    ext_filter = config.FILE_TYPE_EXTENSIONS.get(file_type, [])
    contains_filter = contains_filter.strip().lower()

    files = []
    try:
        # Iterate directory entries
        for entry in os.scandir(folder_path):
            if not entry.is_file():
                continue
            
            file_path = Path(entry.path)
            # Filter by Extension
            if ext_filter and file_path.suffix.lower() not in ext_filter:
                continue
            
            # Filter by Text Content
            if contains_filter and contains_filter not in entry.name.lower():
                continue
            
            files.append(entry.name)
    except OSError as e:
        logging.error(f"Error accessing files in {folder_path}: {e}")
        return [], f"Error accessing files: {e}"
        
    return sorted(files), None

def perform_rename(folder_path: Path, files: List[str], base_name: str, start_num: int, progress_callback: Callable) -> Tuple[List[Dict], List[str]]:
    """
    Executes the rename operation on a list of files.
    Returns: (session_history_list, error_messages_list)
    """
    session_history = []
    errors = []
    counter = start_num
    total_files = len(files)

    for i, f in enumerate(files):
        old_path = folder_path / f
        new_name = generate_new_name(base_name, counter, f)
        new_path = folder_path / new_name
        
        # Safety check: Don't overwrite existing files
        if new_path.exists():
            error_msg = f"Skipped {f}: Target '{new_name}' already exists."
            errors.append(error_msg)
            logging.warning(error_msg)
            progress_callback(i + 1, total_files, f)
            continue
        
        try:
            os.rename(old_path, new_path)
            # Record success for history
            session_history.append({"old": f, "new": new_name})
            counter += 1
        except Exception as e:
            error_msg = f"Failed to rename {f}: {e}"
            errors.append(error_msg)
            logging.error(error_msg)
        
        progress_callback(i + 1, total_files, f)
    
    return session_history, errors

def perform_undo(session: Dict) -> Tuple[int, List[str]]:
    """
    Reverts a rename operation using the session history.
    Processes files in reverse order to avoid conflicts.
    """
    files_undone = 0
    errors = []
    folder = Path(session["folder"])
    
    # Reverse the list to undo the last rename first
    for entry in reversed(session["files"]):
        current_path = folder / entry["new"]
        original_path = folder / entry["old"]
        
        if current_path.exists():
            try:
                os.rename(current_path, original_path)
                files_undone += 1
            except OSError as e:
                err_msg = f"Failed to restore {entry['new']}: {e}"
                errors.append(err_msg)
                logging.error(err_msg)
        else:
            err_msg = f"File not found to undo: {entry['new']}"
            errors.append(err_msg)
            logging.warning(err_msg)
    
    return files_undone, errors

def generate_smart_suggestions(folder_path: Path) -> List[Dict]:
    """
    Analyzes files in the folder and returns smart naming suggestions.
    Strategies: Folder Name, Common Date, Common File Type.
    """
    suggestions = []
    if not folder_path or not folder_path.is_dir():
        return []

    try:
        # Sample up to 50 files for performance
        all_entries = [e for e in os.scandir(folder_path) if e.is_file()]
        sample_files = all_entries[:50]
    except OSError as e:
        logging.error(f"Error scanning for suggestions: {e}")
        return []

    if not sample_files:
        return []

    # 1. Context Analyzer (Folder Name)
    # Clean up folder name (remove special chars, keep spaces/hyphens)
    clean_folder = re.sub(r'[^\w\s-]', '', folder_path.name).strip()
    if clean_folder:
        suggestions.append({
            "value": clean_folder,
            "label": "suggestion_folder",
            "reason": "Based on parent folder name"
        })

    # 2. Temporal Analyzer (Date)
    dates = []
    for entry in sample_files:
        try:
            ts = entry.stat().st_mtime
            dates.append(datetime.fromtimestamp(ts).strftime("%Y-%m-%d"))
        except OSError:
            pass
    
    if dates:
        common_date, count = Counter(dates).most_common(1)[0]
        # Only suggest date if it appears in > 50% of files
        if count >= len(sample_files) * 0.5:
            suggestions.append({
                "value": common_date,
                "label": "suggestion_date",
                "reason": f"Most common date ({count}/{len(sample_files)} files)"
            })

    # 3. Type Analyzer (Extension)
    exts = [Path(e.name).suffix.lower() for e in sample_files]

    if exts:
        common_ext, _ = Counter(exts).most_common(1)[0]
        type_name = "File"
        for cat, ext_list in config.FILE_TYPE_EXTENSIONS.items():
            if common_ext in ext_list:
                # Convert plural category to singular (roughly)
                type_name = cat.rstrip('s')
                break
        
        if not any(s['value'] == type_name for s in suggestions):
            suggestions.append({
                "value": type_name,
                "label": "suggestion_type",
                "reason": f"Based on file extension ({common_ext})"
            })

    return suggestions