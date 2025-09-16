from pathlib import Path
from typing import Optional
import re

def domain_clustering(root: str = '.', k: Optional[int] = None, algorithm: Optional[str] = None) -> dict:
    """Cluster code into domain groups."""
    root_path = Path(root).resolve()
    
    # Simple domain clustering based on directory structure and naming patterns
    domains = {}
    
    # Common domain patterns
    domain_patterns = {
        'auth': ['auth', 'login', 'user', 'permission', 'role', 'session'],
        'api': ['api', 'endpoint', 'route', 'controller', 'handler'],
        'data': ['model', 'schema', 'database', 'repository', 'entity'],
        'ui': ['component', 'view', 'template', 'frontend', 'ui', 'page'],
        'business': ['service', 'business', 'logic', 'workflow', 'process'],
        'infrastructure': ['config', 'setup', 'deploy', 'infra', 'docker'],
        'testing': ['test', 'spec', 'mock', 'fixture'],
        'utils': ['util', 'helper', 'common', 'shared', 'lib']
    }
    
    # Analyze files and directories
    for path in root_path.rglob('*'):
        if '.git' in path.parts or '__pycache__' in path.parts or 'node_modules' in path.parts:
            continue
            
        path_str = str(path.relative_to(root_path)).lower()
        
        # Determine domain based on patterns
        assigned_domain = 'other'
        max_score = 0
        
        for domain, keywords in domain_patterns.items():
            score = sum(1 for keyword in keywords if keyword in path_str)
            if score > max_score:
                max_score = score
                assigned_domain = domain
        
        if assigned_domain not in domains:
            domains[assigned_domain] = {
                'files': [],
                'directories': [],
                'count': 0
            }
        
        if path.is_file():
            domains[assigned_domain]['files'].append(str(path.relative_to(root_path)))
        else:
            domains[assigned_domain]['directories'].append(str(path.relative_to(root_path)))
        
        domains[assigned_domain]['count'] += 1
    
    # Apply clustering parameters if provided
    result = {
        'domains': domains,
        'algorithm': algorithm or 'pattern-based',
        'num_clusters': k or len(domains)
    }
    
    # If k is specified and different from current clusters, merge smallest domains
    if k and k < len(domains):
        sorted_domains = sorted(domains.items(), key=lambda x: x[1]['count'])
        while len(result['domains']) > k:
            smallest = sorted_domains.pop(0)
            # Merge into 'other'
            if 'other' not in result['domains']:
                result['domains']['other'] = smallest[1]
            else:
                result['domains']['other']['files'].extend(smallest[1]['files'])
                result['domains']['other']['directories'].extend(smallest[1]['directories'])
                result['domains']['other']['count'] += smallest[1]['count']
            
            if smallest[0] in result['domains']:
                del result['domains'][smallest[0]]
    
    return result