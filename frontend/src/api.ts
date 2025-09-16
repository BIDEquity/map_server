import { Task, ModuleGraph, DomainClusters } from "./types";
async function get<T>(url: string, fallback: T): Promise<T> {
  try { const res = await fetch(url); if (!res.ok) throw new Error(`HTTP ${res.status}`); return await res.json(); } catch { return fallback; }
}
export const api = {
  tasks: () => get<Task[]>('/api/tasks', []),
  moduleGraph: () => get<ModuleGraph>('/api/graphs/module', { nodes: [], edges: [] }),
  routes: () => get<any[]>('/api/graphs/routes', []),
  domains: () => get<DomainClusters>('/api/domains', { domains: [] }),
  rules: () => get<any[]>('/api/rules', []),
  schemas: () => get<any>('/api/schemas', {}),
  integrations: () => get<any[]>('/api/integrations', []),
  next: () => get<{next: Task|null}>('/api/next', { next: null }),
  progress: () => get<{done:number,in_progress:number,total:number,percent:number}>('/api/progress', {done:0,in_progress:0,total:0,percent:0}),
  setTaskStatus: async (id: number, status: string) => {
    const res = await fetch(`/api/tasks/${id}/status`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) });
    return res.json();
  },
  beginNext: async () => (await fetch('/api/next/begin', { method: 'POST' })).json(),
  completeNext: async () => (await fetch('/api/next/complete', { method: 'POST' })).json(),
}
