from pathlib import Path
import subprocess
import json

def inventory(root: str = '.') -> dict:
    """Create an inventory of repository components."""
    root_path = Path(root).resolve()
    
    inventory_data = {
        'root': str(root_path),
        'git_info': {},
        'languages': {},
        'frameworks': [],
        'configuration_files': []
    }
    
    # Check git info
    try:
        result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], 
                              cwd=root_path, capture_output=True, text=True)
        if result.returncode == 0:
            inventory_data['git_info']['repo_root'] = result.stdout.strip()
            
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                  cwd=root_path, capture_output=True, text=True)
            if result.returncode == 0:
                inventory_data['git_info']['current_branch'] = result.stdout.strip()
    except:
        pass
    
    # Detect languages by file extensions
    lang_extensions = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.jsx': 'React',
        '.tsx': 'React TypeScript',
        '.java': 'Java',
        '.go': 'Go',
        '.rs': 'Rust',
        '.cpp': 'C++',
        '.c': 'C'
    }
    
    for path in root_path.rglob('*'):
        if path.is_file() and path.suffix in lang_extensions:
            lang = lang_extensions[path.suffix]
            if lang not in inventory_data['languages']:
                inventory_data['languages'][lang] = 0
            inventory_data['languages'][lang] += 1
    
    # Check for common framework files
    framework_files = {
        'package.json': 'Node.js',
        'requirements.txt': 'Python',
        'pyproject.toml': 'Python',
        'Cargo.toml': 'Rust',
        'go.mod': 'Go',
        'pom.xml': 'Maven',
        'build.gradle': 'Gradle'
    }
    
    for filename, framework in framework_files.items():
        if (root_path / filename).exists():
            inventory_data['frameworks'].append(framework)
            inventory_data['configuration_files'].append(filename)
    
    return inventory_data