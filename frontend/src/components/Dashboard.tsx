import { useEffect, useState } from 'react'
import { api } from '../api'
import { Task } from '../types'
import { Link } from 'react-router-dom'

export default function Dashboard({ tasks, onRefresh }: { tasks: Task[], onRefresh: () => void }) {
  const [routes, setRoutes] = useState<any[]>([])
  const [domains, setDomains] = useState<{ domains: any[] }>({ domains: [] })
  const [integrations, setIntegrations] = useState<any[]>([])
  const [nextTask, setNextTask] = useState<Task | null>(null)
  const [progress, setProgress] = useState<{done:number,in_progress:number,total:number,percent:number}>({done:0,in_progress:0,total:0,percent:0})

  const refreshAll = async () => {
    onRefresh()
    api.routes().then(setRoutes)
    api.domains().then(setDomains)
    api.integrations().then(setIntegrations)
    api.next().then(r => setNextTask(r.next))
    api.progress().then(setProgress)
  }

  useEffect(() => { refreshAll() }, [])

  const current = tasks.find(t => t.status === 'in_progress') || nextTask

  return (
    <div className="grid">
      <div className="panel">
        <div className="section-title">Overall progress</div>
        <div className="progress" style={{marginBottom: 8}}><div style={{width: progress.percent+'%'}} /></div>
        <div className="small">{progress.done} done • {progress.in_progress} in-progress • {progress.total} total</div>

        <div style={{marginTop: 16}}>
          <div className="section-title">Current / Next task</div>
          {current ? (
            <div className="task-card">
              <div className="task-title"><Link to={`/tasks/${current.id}`}>{current.title}</Link> <span className="status">({current.status})</span></div>
              <div className="small">{current.description}</div>
              <div style={{marginTop:8}}>
                <button onClick={async ()=>{ await api.beginNext(); await refreshAll(); }}>Begin next</button>{' '}
                <button onClick={async ()=>{ await api.completeNext(); await refreshAll(); }}>Complete next</button>
              </div>
            </div>
          ) : <div className="small">No task selected yet.</div>}
        </div>

        <div style={{marginTop: 16}}>
          <button onClick={refreshAll}>Refresh</button>
        </div>
      </div>

      <div>
        <div className="panel">
          <div className="section-title">Domains</div>
          <div className="small">{domains.domains.length} domain groups</div>
          <ul>
            {domains.domains.slice(0,6).map(d => (
              <li key={d.name}>{d.name} <span className="small">({d.modules.length} modules)</span></li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <div className="section-title">External services</div>
          <div className="small">{integrations.length} detected clients</div>
          <ul>
            {integrations.slice(0,8).map((i, idx) => (
              <li key={idx}>{i.service} <span className="small">({i.type})</span></li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <div className="section-title">Top routes</div>
          <ul>
            {routes.slice(0,8).map((r, idx) => (
              <li key={idx}>{r.method} {r.path}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
