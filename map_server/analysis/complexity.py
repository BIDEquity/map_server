from pathlib import Path
from typing import Optional
import ast
import subprocess

def complexity_and_hotspots(root: str = '.', since: Optional[str] = None) -> list:
    """Analyze code complexity and identify hotspots."""
    root_path = Path(root).resolve()
    hotspots = []
    
    # Analyze Python files for complexity
    for py_file in root_path.rglob('*.py'):
        if '.git' in py_file.parts or '__pycache__' in py_file.parts:
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            file_info = {
                'file': str(py_file.relative_to(root_path)),
                'complexity': 0,
                'lines': len(content.splitlines()),
                'functions': 0,
                'classes': 0,
                'git_changes': 0
            }
            
            # Count complexity indicators
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    file_info['functions'] += 1
                    # Simple cyclomatic complexity: count decision points
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                            file_info['complexity'] += 1
                elif isinstance(node, ast.ClassDef):
                    file_info['classes'] += 1
                    file_info['complexity'] += 1
            
            # Try to get git change frequency
            if (root_path / '.git').exists():
                try:
                    cmd = ['git', 'log', '--oneline']
                    if since:
                        cmd.append(f'--since={since}')
                    cmd.append('--')
                    cmd.append(str(py_file))
                    
                    result = subprocess.run(cmd, cwd=root_path, capture_output=True, text=True)
                    if result.returncode == 0:
                        file_info['git_changes'] = len(result.stdout.strip().splitlines())
                except:
                    pass
            
            # Calculate hotspot score
            file_info['hotspot_score'] = (
                file_info['complexity'] * 2 +
                file_info['git_changes'] * 3 +
                (file_info['lines'] / 100)
            )
            
            hotspots.append(file_info)
        except:
            pass
    
    # Sort by hotspot score
    hotspots.sort(key=lambda x: x['hotspot_score'], reverse=True)
    
    return hotspots