import React, { useEffect, useMemo, useState } from 'react'

type Sample = {
  id: string
  full_path: string
  filename: string
  ext: string
  size_bytes: number
  bpm?: number
  sample_rate?: number
  channels?: number
  instrument_hint?: string
  fuzzy_score?: number
  added_at?: string
}

export default function SamplesList({ onSelect }: { onSelect?: (row: Sample) => void }) {
  const [rows, setRows] = useState<Sample[]>([])
  const [loading, setLoading] = useState(false)
  const [sortBy, setSortBy] = useState<string>('added_at')
  const [sortDir, setSortDir] = useState<'asc'|'desc'>('desc')
  const [limit, setLimit] = useState<number>(100)
  const [page, setPage] = useState<number>(0)
  // Filters
  const [search, setSearch] = useState<string>('')
  const [instrument, setInstrument] = useState<string>('')
  const [ext, setExt] = useState<string>('')
  const [bpmMin, setBpmMin] = useState<string>('')
  const [bpmMax, setBpmMax] = useState<string>('')

  const fetchRows = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('sort_by', sortBy)
      params.set('sort_dir', sortDir)
      params.set('limit', String(limit))
      params.set('offset', String(page * limit))
      if (instrument.trim()) params.set('instrument', instrument.trim())
      const resp = await fetch(`/samples?${params.toString()}`)
      if (resp.ok) {
        const j = await resp.json()
        setRows(j.rows || [])
      }
    } catch (e) {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchRows() }, [sortBy, sortDir, limit, page, instrument])

  const instrumentOptions = useMemo(() => {
    const set = new Set<string>()
    rows.forEach(r => { if (r.instrument_hint) set.add(r.instrument_hint) })
    return Array.from(set).sort()
  }, [rows])

  const extOptions = useMemo(() => {
    const set = new Set<string>()
    rows.forEach(r => { if (r.ext) set.add(r.ext) })
    return Array.from(set).sort()
  }, [rows])

  const filtered = useMemo(() => {
    return rows.filter(r => {
      if (search && !r.filename.toLowerCase().includes(search.toLowerCase())) return false
      const bpm = typeof r.bpm === 'number' ? r.bpm : undefined
      if (bpmMin && (bpm === undefined || bpm < Number(bpmMin))) return false
      if (bpmMax && (bpm === undefined || bpm > Number(bpmMax))) return false
      if (ext && r.ext !== ext) return false
      return true
    })
  }, [rows, search, bpmMin, bpmMax])

  const toggleSort = (col: string) => {
    if (col === sortBy) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(col)
      setSortDir('desc')
    }
  }

  return (
    <div className="p-4 border rounded bg-white shadow-sm">
      <h2 className="text-lg font-medium">Samples</h2>
      {/* Filters */}
      <div className="mt-3 grid grid-cols-6 gap-2 items-end">
        <div className="col-span-2">
          <label className="block text-xs text-gray-600">Search</label>
          <input className="border p-1 w-full" value={search} onChange={e => { setSearch(e.target.value); }} placeholder="filename contains..." />
        </div>
        <div>
          <label className="block text-xs text-gray-600">Instrument</label>
          <select className="border p-1 w-full" value={instrument} onChange={e => { setPage(0); setInstrument(e.target.value) }}>
            <option value="">All</option>
            {instrumentOptions.map(opt => (<option key={opt} value={opt}>{opt}</option>))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-600">Ext</label>
          <select className="border p-1 w-full" value={ext} onChange={e => setExt(e.target.value)}>
            <option value="">All</option>
            {extOptions.map(opt => (<option key={opt} value={opt}>{opt}</option>))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-600">BPM Min</label>
          <input type="number" className="border p-1 w-full" value={bpmMin} onChange={e => setBpmMin(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-gray-600">BPM Max</label>
          <input type="number" className="border p-1 w-full" value={bpmMax} onChange={e => setBpmMax(e.target.value)} />
        </div>
        <div className="flex space-x-2">
          <div>
            <label className="block text-xs text-gray-600">Limit</label>
            <select className="border p-1" value={String(limit)} onChange={e => { setPage(0); setLimit(Number(e.target.value)) }}>
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="250">250</option>
            </select>
          </div>
          <div className="self-end space-x-2">
            <button className="px-2 py-1 border rounded" onClick={() => { setSearch(''); setInstrument(''); setExt(''); setBpmMin(''); setBpmMax(''); }}>Clear</button>
            <button className="px-2 py-1 border rounded" onClick={() => { setPage(0); fetchRows(); }}>Refresh</button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="mt-3">
        {loading ? (<div>Loading...</div>) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                <th className="px-2 py-1 text-left cursor-pointer" onClick={() => toggleSort('filename')}>Filename</th>
                <th className="px-2 py-1 text-right cursor-pointer" onClick={() => toggleSort('size_bytes')}>Size</th>
                <th className="px-2 py-1 text-right cursor-pointer" onClick={() => toggleSort('bpm')}>BPM</th>
                <th className="px-2 py-1 text-right cursor-pointer" onClick={() => toggleSort('sample_rate')}>SR</th>
                <th className="px-2 py-1">Instrument</th>
                <th className="px-2 py-1">Added</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => (
                <tr key={r.id} className="border-t hover:bg-gray-50 cursor-pointer" onClick={() => onSelect?.(r)}>
                  <td className="px-2 py-1">{r.filename}</td>
                  <td className="px-2 py-1 text-right">{r.size_bytes}</td>
                  <td className="px-2 py-1 text-right">{r.bpm ? Math.round(r.bpm) : ''}</td>
                  <td className="px-2 py-1 text-right">{r.sample_rate || ''}</td>
                  <td className="px-2 py-1">{r.instrument_hint || ''}</td>
                  <td className="px-2 py-1">{r.added_at || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      <div className="mt-2 flex items-center justify-between text-xs text-gray-600">
        <div>Rows: {filtered.length} (page {page + 1})</div>
        <div className="space-x-2">
          <button className="px-2 py-1 border rounded disabled:opacity-50" disabled={page === 0} onClick={() => setPage(p => Math.max(0, p - 1))}>Prev</button>
          <button className="px-2 py-1 border rounded" onClick={() => setPage(p => p + 1)}>Next</button>
        </div>
      </div>
    </div>
  )
}
