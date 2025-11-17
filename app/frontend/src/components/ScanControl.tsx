import React, { useEffect, useState, useRef } from 'react'
import ExportPreview from './ExportPreview'
let invoke: ((cmd: string, args?: any) => Promise<any>) | null = null
try {
  // dynamically import Tauri invoke if available at runtime
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  // @ts-ignore
  const tauri = require('@tauri-apps/api')
  invoke = tauri.invoke
} catch (e) {
  // not running in Tauri / not available
  invoke = null
}

type JobStatus = {
  id: string
  status: string
  started_at?: number
  finished_at?: number
  cancel_requested?: number
  result?: any
}

export default function ScanControl() {
  const [backend, setBackend] = useState<string>('http://localhost:8000')
  const [roots, setRoots] = useState<string>('')
  const [dbPath, setDbPath] = useState<string>('')
  const [batchSize, setBatchSize] = useState<number>(100)
  const [minSize, setMinSize] = useState<number>(512)
  const [job, setJob] = useState<JobStatus | null>(null)
  const [plannedMoves, setPlannedMoves] = useState<Array<{src:string;dst:string}>>([])
  const pollingRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (pollingRef.current) window.clearInterval(pollingRef.current)
    }
  }, [])

  const startScan = async () => {
    const rootsArr = roots.split(',').map(s => s.trim()).filter(Boolean)
    const resp = await fetch(`${backend}/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ roots: rootsArr, db_path: dbPath || undefined, batch_size: batchSize, min_size: minSize }),
    })
    const j = await resp.json()
    if (j.job_id) {
      const jobObj: JobStatus = { id: j.job_id, status: 'running' }
      setJob(jobObj)
      startPolling(j.job_id)
    }
  }

  const runDryRun = async () => {
    const rootsArr = roots.split(',').map(s => s.trim()).filter(Boolean)
    try {
      const resp = await fetch(`${backend}/scan/dryrun`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ roots: rootsArr, db_path: dbPath || undefined, batch_size: batchSize, min_size: minSize }),
      })
      const j = await resp.json()
      // `scan_roots` returns planned_move_examples when dry_run=True
      if (j && j.planned_move_examples) {
        setPlannedMoves(j.planned_move_examples.map((t: any) => ({ src: t[0], dst: t[1] })))
      }
      // also show summary in job area
      setJob({ id: 'dryrun', status: 'done', result: j })
    } catch (e) {
      console.warn('dryrun failed', e)
    }
  }

  const pickFolder = async () => {
    if (!invoke) return
    try {
      const path = await invoke('pick_folder')
      if (path) {
        setRoots(path)
      }
    } catch (e) {
      console.warn('pick_folder failed', e)
    }
  }

  const startPolling = (jobId: string) => {
    if (pollingRef.current) window.clearInterval(pollingRef.current)
    pollingRef.current = window.setInterval(async () => {
      try {
        const r = await fetch(`${backend}/scan/${jobId}`)
        if (r.status === 200) {
          const data = await r.json()
          setJob(data)
          if (['done', 'failed'].includes(data.status)) {
            if (pollingRef.current) window.clearInterval(pollingRef.current)
            pollingRef.current = null
          }
        }
      } catch (e) {
        // ignore
      }
    }, 1000)
  }

  const cancel = async () => {
    if (!job) return
    await fetch(`${backend}/scan/${job.id}/cancel?db_path=${encodeURIComponent(dbPath)}`, { method: 'POST' })
    // optimistic update
    setJob(j => j ? { ...j, cancel_requested: 1 } : j)
  }

  return (
    <div className="p-4 border rounded bg-white shadow-sm">
      <h2 className="text-lg font-medium">Scan Control</h2>
      <div className="grid grid-cols-2 gap-2 mt-3">
        <label className="text-sm">Backend URL</label>
        <input className="border p-1" value={backend} onChange={e => setBackend(e.target.value)} />
        <label className="text-sm">Roots (comma-separated)</label>
        <input className="border p-1" value={roots} onChange={e => setRoots(e.target.value)} placeholder="/path/to/samples" />
        <label className="text-sm">DB Path (optional)</label>
        <input className="border p-1" value={dbPath} onChange={e => setDbPath(e.target.value)} placeholder="/tmp/kass.db" />
        <label className="text-sm">Batch Size</label>
        <input type="number" className="border p-1" value={String(batchSize)} onChange={e => setBatchSize(Number(e.target.value))} />
        <label className="text-sm">Min Size (bytes)</label>
        <input type="number" className="border p-1" value={String(minSize)} onChange={e => setMinSize(Number(e.target.value))} />
      </div>
      <div className="mt-3 space-x-2">
        <button className="px-3 py-1 bg-blue-600 text-white rounded" onClick={startScan}>Start Scan</button>
        <button className="px-3 py-1 bg-yellow-600 text-white rounded" onClick={runDryRun}>Dry Run</button>
        <button className="px-3 py-1 bg-red-500 text-white rounded" onClick={cancel} disabled={!job}>Cancel</button>
        <button className="px-3 py-1 bg-gray-200 text-black rounded" onClick={pickFolder}>Pick Folder</button>
      </div>

      {job && (
        <div className="mt-3 p-2 bg-gray-50 border rounded">
          <div><strong>Job ID:</strong> {job.id}</div>
          <div><strong>Status:</strong> {job.status}</div>
          <div><strong>Cancel Requested:</strong> {job.cancel_requested ? 'Yes' : 'No'}</div>
          <div><strong>Result:</strong> <pre className="text-xs">{JSON.stringify(job.result || {}, null, 2)}</pre></div>
          {plannedMoves && plannedMoves.length > 0 && (
            <div className="mt-2">
              <ExportPreview moves={plannedMoves} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
