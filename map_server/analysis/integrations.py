from pathlib import Path
import re
import json

def external_integrations(root: str = '.') -> list:
    """Identify external integrations and APIs."""
    root_path = Path(root).resolve()
    integrations = []
    
    # Patterns to identify external integrations
    patterns = {
        'database': [
            (r'(mongodb|mysql|postgresql|redis|sqlite|dynamodb)', 'Database'),
            (r'(SELECT|INSERT|UPDATE|DELETE)\s+FROM', 'SQL Query')
        ],
        'api': [
            (r'https?://[^\s\'"]+', 'HTTP API'),
            (r'(fetch|axios|requests)\.(get|post|put|delete)', 'HTTP Client')
        ],
        'cloud': [
            (r'(aws|azure|gcp|google\.cloud)', 'Cloud Provider'),
            (r'(s3|ec2|lambda|cloudfront)', 'AWS Service'),
            (r'(blob\.core\.windows|azure)', 'Azure Service')
        ],
        'messaging': [
            (r'(kafka|rabbitmq|sqs|sns|pubsub)', 'Message Queue'),
            (r'(websocket|socket\.io)', 'WebSocket')
        ],
        'auth': [
            (r'(oauth|jwt|auth0|okta|firebase\.auth)', 'Authentication'),
            (r'(bearer|api[_-]?key)', 'API Authentication')
        ]
    }
    
    seen = set()
    
    for file_path in root_path.rglob('*'):
        if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.java', '.go']:
            if '.git' in file_path.parts or 'node_modules' in file_path.parts:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for category, category_patterns in patterns.items():
                    for pattern, integration_type in category_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        for match in matches:
                            key = f"{category}:{integration_type}:{match}"
                            if key not in seen:
                                seen.add(key)
                                integrations.append({
                                    'category': category,
                                    'type': integration_type,
                                    'value': match if isinstance(match, str) else match[0],
                                    'file': str(file_path.relative_to(root_path))
                                })
            except:
                pass
    
    return integrations