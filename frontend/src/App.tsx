import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/status')
      .then(res => res.json())
      .then(data => {
        setData(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch status:', err)
        setLoading(false)
      })
  }, [])

  return (
    <div className="App">
      <h1>Map Server Dashboard</h1>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <div>
          <h2>Server Status</h2>
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}

export default App