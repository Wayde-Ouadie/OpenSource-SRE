import React from 'react'

export default function App() {
  const [backend, setBackend] = React.useState({ status: 'unknown' })

  React.useEffect(() => {
    let cancelled = false
    fetch('/api/health')
      .then(async (r) => {
        const data = await r.json().catch(() => ({}))
        if (!cancelled) setBackend({ http: r.status, ...data })
      })
      .catch((e) => {
        if (!cancelled) setBackend({ status: 'error', error: String(e) })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: 24, lineHeight: 1.4 }}>
      <h1 style={{ margin: 0 }}>DevOps Incident & On-Call Platform</h1>
      <p style={{ marginTop: 8 }}>
        Web UI skeleton (local edition). Backend connectivity check below.
      </p>

      <h2 style={{ marginTop: 24 }}>Backend health</h2>
      <pre style={{ padding: 12, overflowX: 'auto' }}>
        {JSON.stringify(backend, null, 2)}
      </pre>
    </div>
  )
}
