from pathlib import Path
import json
import os

def build_index(root: str = '.') -> dict:
    """Build an index of the repository structure."""
    root_path = Path(root).resolve()
    
    index = {
        'root': str(root_path),
        'files': [],
        'directories': [],
        'stats': {
            'total_files': 0,
            'total_dirs': 0,
            'total_size': 0
        }
    }
    
    for path in root_path.rglob('*'):
        if path.is_file():
            if '.git' not in path.parts and '__pycache__' not in path.parts:
                index['files'].append(str(path.relative_to(root_path)))
                index['stats']['total_files'] += 1
                try:
                    index['stats']['total_size'] += path.stat().st_size
                except:
                    pass
        elif path.is_dir():
            if '.git' not in path.parts and '__pycache__' not in path.parts:
                index['directories'].append(str(path.relative_to(root_path)))
                index['stats']['total_dirs'] += 1
    
    return index