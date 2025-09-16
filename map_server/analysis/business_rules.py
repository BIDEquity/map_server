from pathlib import Path
from typing import Optional, List
import re
import ast

def business_rules(root: str = '.', module_globs: Optional[List[str]] = None) -> list:
    """Extract business rules and logic from code."""
    root_path = Path(root).resolve()
    rules = []
    
    # Patterns that indicate business logic
    business_patterns = [
        # Validation rules
        (r'if\s+.*?(valid|check|verify|ensure)', 'validation'),
        (r'raise\s+.*?Error', 'error_handling'),
        (r'assert\s+', 'assertion'),
        
        # Business calculations
        (r'(calculate|compute|total|sum|average)', 'calculation'),
        (r'(price|cost|fee|rate|discount)', 'pricing'),
        (r'(limit|threshold|maximum|minimum)', 'constraint'),
        
        # State transitions
        (r'(status|state)\s*=', 'state_change'),
        (r'(approve|reject|pending|complete)', 'workflow'),
        
        # Business conditions
        (r'if\s+.*?(expired|active|enabled|disabled)', 'condition'),
        (r'(before|after|during|between)', 'temporal'),
    ]
    
    # Process files
    for file_path in root_path.rglob('*.py'):
        if '.git' in file_path.parts or '__pycache__' in file_path.parts:
            continue
            
        # Check glob patterns if provided
        if module_globs:
            path_str = str(file_path.relative_to(root_path))
            if not any(Path(path_str).match(glob) for glob in module_globs):
                continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Look for business rules
            for i, line in enumerate(lines, 1):
                for pattern, rule_type in business_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Get context (surrounding lines)
                        start = max(0, i - 2)
                        end = min(len(lines), i + 2)
                        context = '\\n'.join(lines[start:end])
                        
                        rules.append({
                            'file': str(file_path.relative_to(root_path)),
                            'line': i,
                            'type': rule_type,
                            'code': line.strip(),
                            'context': context
                        })
            
            # Also look for function/method names that suggest business logic
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        name_lower = node.name.lower()
                        if any(keyword in name_lower for keyword in 
                               ['validate', 'check', 'calculate', 'process', 'handle',
                                'approve', 'reject', 'authorize', 'verify']):
                            
                            # Get function docstring if available
                            docstring = ast.get_docstring(node) or ''
                            
                            rules.append({
                                'file': str(file_path.relative_to(root_path)),
                                'line': node.lineno,
                                'type': 'business_function',
                                'code': f'def {node.name}(...)',
                                'context': docstring[:200] if docstring else ''
                            })
            except:
                pass
                
        except:
            pass
    
    return rules