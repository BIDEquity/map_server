from pathlib import Path
from typing import Optional, List
import re

def route_extraction(root: str = '.', limit: Optional[int] = None) -> list:
    """Extract API routes from the codebase."""
    root_path = Path(root).resolve()
    routes = []
    
    # Common route patterns for different frameworks
    patterns = [
        # Flask/FastAPI
        (r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', 'Flask/FastAPI'),
        (r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', 'FastAPI Router'),
        # Express.js
        (r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', 'Express'),
        (r'router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', 'Express Router'),
        # Django
        (r'path\(["\']([^"\']+)["\']', 'Django'),
        # Rails
        (r'(get|post|put|delete|patch)\s+["\']([^"\']+)["\']', 'Rails')
    ]
    
    # Search through Python and JavaScript files
    for ext in ['*.py', '*.js', '*.ts']:
        for file_path in root_path.rglob(ext):
            if '.git' in file_path.parts or 'node_modules' in file_path.parts:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern, framework in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            method = match[0] if len(match) > 1 else 'GET'
                            path = match[1] if len(match) > 1 else match[0]
                        else:
                            method = 'GET'
                            path = match
                            
                        routes.append({
                            'method': method.upper(),
                            'path': path,
                            'file': str(file_path.relative_to(root_path)),
                            'framework': framework
                        })
                        
                        if limit and len(routes) >= limit:
                            return routes
            except:
                pass
    
    return routes