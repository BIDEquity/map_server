export interface Task {
  id: number;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'done' | 'blocked';
  priority?: 'low' | 'medium' | 'high';
  dependencies?: number[];
  subtasks?: Task[];
}

export interface ModuleGraph {
  nodes: ModuleNode[];
  edges: ModuleEdge[];
}

export interface ModuleNode {
  id: string;
  label: string;
  type?: string;
  size?: number;
}

export interface ModuleEdge {
  source: string;
  target: string;
  type?: string;
}

export interface DomainClusters {
  domains: Domain[];
}

export interface Domain {
  name: string;
  files: string[];
  directories: string[];
  count: number;
}