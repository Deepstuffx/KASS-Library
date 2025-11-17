import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { fileUrl } from '../utils/tauri'

type Sample = {
  id: string
  full_path: string
  filename: string
  ext?: string
  size_bytes?: number
  bpm?: number | null
  sample_rate?: number | null
  channels?: number | null
  instrument_hint?: string | null
  added_at?: string | null
}

type FetchResult = { rows: Sample[]; total: number }

async function fetchPage(page: number, size: number, sortBy: string, sortDir: 'asc'|'desc', filters: Record<string,string>): Promise<FetchResult> {
  const params = new URLSearchParams()
  params.set('limit', String(size))
  params.set('offset', String(page * size))
  params.set('sort_by', sortBy)
  params.set('sort_dir', sortDir)
  Object.entries(filters).forEach(([k,v]) => { if (v) params.set(k, v) })
  const resp = await fetch(`/samples?${params.toString()}`)
  if (!resp.ok) return { rows: [], total: 0 }
  const j = await resp.json()
  return { rows: j.rows || [], total: j.total || (j.rows?.length ?? 0) }
}

export default function SamplesVirtualTable() {
  const parentRef = useRef<HTMLDivElement | null>(null)
  const [rows, setRows] = useState<Sample[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [limit, setLimit] = useState(100)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<Sample | null>(null)
  const [sortBy, setSortBy] = useState('added_at')
  const [sortDir, setSortDir] = useState<'asc'|'desc'>('desc')
  const [search, setSearch] = useState('')

  useEffect(() => {
    let cancel = false
    setLoading(true)
    fetchPage(page, limit, sortBy, sortDir, { q: search.trim() })
      .then(({ rows: r, total: t }) => {
        if (cancel) return
        setTotal(t)
        setRows(prev => page === 0 ? r : [...prev, ...r])
      })
      .finally(() => { if (!cancel) setLoading(false) })
    return () => { cancel = true }
  }, [page, limit, sortBy, sortDir, search])

  const rowVirtualizer = useVirtualizer({
    count: Math.max(total, rows.length),
    getScrollElement: () => parentRef.current,
    estimateSize: () => 36,
    overscan: 12,
  })

  useEffect(() => {
    const items = rowVirtualizer.getVirtualItems()
    const last = items[items.length - 1]
    if (!last) return
    const loaded = rows.length
    if (last.index >= loaded - 5 && loaded < total && !loading) {
      setPage(p => p + 1)
    }
  }, [rowVirtualizer.getVirtualItems(), rows.length, total, loading])

  const toggleSort = (col: string) => {
    if (col === sortBy) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortBy(col); setSortDir('desc'); setPage(0) }
  }

  const selectedUrl = useMemo(() => fileUrl(selected?.full_path || ''), [selected])

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-3 py-2 border-b border-slate-800 bg-[#0b1220] text-sm flex items-end gap-2">
        <div className="flex-1 max-w-md">
          <input className="w-full bg-slate-800/60 text-slate-200 placeholder-slate-400 px-2 py-1 rounded border border-slate-700 focus:border-slate-500"
                 placeholder="Search filename…"
                 value={search}
                 onChange={e => { setPage(0); setRows([]); setSearch(e.target.value) }} />
        </div>
        <label className="text-slate-400 text-xs">Page Size</label>
        <select className="bg-slate-800 text-slate-200 border border-slate-700 rounded px-2 py-1"
                value={String(limit)} onChange={e => { setPage(0); setRows([]); setLimit(Number(e.target.value)) }}>
          <option value="50">50</option>
          <option value="100">100</option>
          <option value="250">250</option>
        </select>
        {loading && <div className="text-slate-400 text-xs">Loading…</div>}
      </div>

      <div className="grid grid-cols-[1fr_auto_auto_auto_auto_auto] gap-x-2 text-xs px-3 py-2 bg-[#0b1220] text-slate-400 sticky top-0">
        <button onClick={() => toggleSort('filename')} className="text-left">Filename</button>
        <button onClick={() => toggleSort('size_bytes')} className="text-right">Size</button>
        <button onClick={() => toggleSort('bpm')} className="text-right">BPM</button>
        <button onClick={() => toggleSort('sample_rate')} className="text-right">SR</button>
        <button onClick={() => toggleSort('instrument_hint')} className="text-left">Instrument</button>
        <button onClick={() => toggleSort('added_at')} className="text-left">Added</button>
      </div>

      <div ref={parentRef} className="flex-1 overflow-auto">
        <div style={{ height: rowVirtualizer.getTotalSize(), position: 'relative' }}>
          {rowVirtualizer.getVirtualItems().map(vi => {
            const r = rows[vi.index]
            if (!r) return null
            return (
              <div key={r.id}
                   style={{ position: 'absolute', top: 0, left: 0, right: 0, transform: `translateY(${vi.start}px)` }}
                   className={`grid grid-cols-[1fr_auto_auto_auto_auto_auto] gap-x-2 text-sm px-3 h-9 items-center border-b border-slate-800/50 ${selected?.id === r.id ? 'bg-slate-800/40' : 'hover:bg-slate-800/20'}`}
                   onClick={() => setSelected(r)}>
                <div className="truncate text-slate-200">{r.filename}</div>
                <div className="text-right text-slate-400">{r.size_bytes ?? ''}</div>
                <div className="text-right text-slate-400">{r.bpm ? Math.round(r.bpm) : ''}</div>
                <div className="text-right text-slate-400">{r.sample_rate ?? ''}</div>
                <div className="text-slate-400">{r.instrument_hint ?? ''}</div>
                <div className="text-slate-400">{r.added_at ?? ''}</div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="border-t border-slate-800 p-3 bg-[#0b1220]">
        {selected ? (
          <div className="space-y-2">
            <div className="text-slate-300 text-sm">Preview: {selected.filename}</div>
            {selectedUrl ? <audio controls src={selectedUrl} preload="none" /> : <div className="text-slate-500 text-sm">No audio URL</div>}
          </div>
        ) : (
          <div className="text-slate-500 text-sm">Select a row to preview</div>
        )}
      </div>
    </div>
  )
}
