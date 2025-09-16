from pathlib import Path
from typing import Optional, List
import re
import json
import ast

def schemas_extract(root: str = '.', include: Optional[List[str]] = None) -> dict:
    """Extract data schemas from the codebase."""
    root_path = Path(root).resolve()
    schemas = {}
    
    # Python class definitions (dataclasses, pydantic models, etc.)
    for py_file in root_path.rglob('*.py'):
        if '.git' in py_file.parts or '__pycache__' in py_file.parts:
            continue
            
        if include and not any(inc in str(py_file) for inc in include):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        'type': 'class',
                        'file': str(py_file.relative_to(root_path)),
                        'fields': []
                    }
                    
                    # Extract class attributes
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            field_type = ast.unparse(item.annotation) if hasattr(ast, 'unparse') else str(item.annotation)
                            class_info['fields'].append({
                                'name': item.target.id,
                                'type': field_type
                            })
                    
                    if class_info['fields']:
                        schemas[node.name] = class_info
        except:
            pass
    
    # JSON Schema files
    for json_file in root_path.rglob('*.json'):
        if '.git' in json_file.parts or 'node_modules' in json_file.parts:
            continue
            
        if include and not any(inc in str(json_file) for inc in include):
            continue
            
        if 'schema' in json_file.name.lower():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if '$schema' in data or 'type' in data or 'properties' in data:
                    schemas[json_file.stem] = {
                        'type': 'json-schema',
                        'file': str(json_file.relative_to(root_path)),
                        'schema': data
                    }
            except:
                pass
    
    # TypeScript interfaces
    for ts_file in root_path.rglob('*.ts'):
        if '.git' in ts_file.parts or 'node_modules' in ts_file.parts:
            continue
            
        if include and not any(inc in str(ts_file) for inc in include):
            continue
            
        try:
            with open(ts_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Simple regex to find interfaces
            interface_pattern = r'interface\s+(\w+)\s*\{([^}]+)\}'
            matches = re.findall(interface_pattern, content)
            
            for name, body in matches:
                fields = []
                field_pattern = r'(\w+)\s*:\s*([^;,\n]+)'
                field_matches = re.findall(field_pattern, body)
                
                for field_name, field_type in field_matches:
                    fields.append({
                        'name': field_name.strip(),
                        'type': field_type.strip()
                    })
                
                if fields:
                    schemas[name] = {
                        'type': 'typescript-interface',
                        'file': str(ts_file.relative_to(root_path)),
                        'fields': fields
                    }
        except:
            pass
    
    return schemas