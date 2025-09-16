from pathlib import Path
import ast
import json

def module_graph(root: str = '.', include_third_party: bool = False) -> dict:
    """Generate a module dependency graph."""
    root_path = Path(root).resolve()
    
    graph = {
        'modules': {},
        'dependencies': [],
        'external': []
    }
    
    # Find all Python files
    for py_file in root_path.rglob('*.py'):
        if '.git' in py_file.parts or '__pycache__' in py_file.parts:
            continue
            
        module_name = str(py_file.relative_to(root_path))[:-3].replace('/', '.')
        graph['modules'][module_name] = {
            'path': str(py_file.relative_to(root_path)),
            'imports': []
        }
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        import_name = alias.name
                        graph['modules'][module_name]['imports'].append(import_name)
                        
                        if import_name.startswith('.') or import_name.split('.')[0] in graph['modules']:
                            graph['dependencies'].append({
                                'from': module_name,
                                'to': import_name
                            })
                        elif include_third_party:
                            graph['external'].append({
                                'module': module_name,
                                'imports': import_name
                            })
                            
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        import_name = node.module
                        graph['modules'][module_name]['imports'].append(import_name)
                        
                        if import_name.startswith('.') or import_name.split('.')[0] in graph['modules']:
                            graph['dependencies'].append({
                                'from': module_name,
                                'to': import_name
                            })
                        elif include_third_party:
                            graph['external'].append({
                                'module': module_name,
                                'imports': import_name
                            })
        except:
            pass
    
    return graph