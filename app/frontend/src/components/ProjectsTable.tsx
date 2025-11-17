import React from 'react'

type Row = {
  id: number
  name: string
  tempo: number
  genre?: string
  progress?: number
  tier?: string
  key?: string
  tags?: string[]
  created?: string
}

const rows: Row[] = Array.from({ length: 15 }).map((_, i) => ({
  id: i + 1,
  name: [
    'Bass House pattern practice Project',
    'catt Project',
    'clown house Project',
    'complicated Project',
    'dale Project',
    'Dawn Project',
    'digital ocean Project',
    'doot doot Project',
    'Dreem Project',
    'edgelord Project',
    'experiment again Project',
    'Extral. (SimplyKam! Remix) Project',
    'Generic kpop sign GG Project',
    'guitar arp Project',
    'Hardest drums Project',
  ][i % 15],
  tempo: [126, 150, 126, 155, 95, 155, 126, 164, 110, 100, 146, 145, 126, 145, 95][i % 15],
  genre: '',
  progress: undefined,
  tier: '',
  key: '',
  tags: [],
  created: '09/17/25',
}))

export default function ProjectsTable() {
  return (
    <div className="flex-1 overflow-auto">
      <table className="min-w-full text-sm text-slate-200">
        <thead className="sticky top-0 bg-[#0b1220] border-b border-slate-800">
          <tr>
            <th className="px-3 py-2 text-left w-10">#</th>
            <th className="px-3 py-2 text-left w-16">Open</th>
            <th className="px-3 py-2 text-left w-16">Play</th>
            <th className="px-3 py-2 text-left">Name <span className="text-slate-500">↑</span></th>
            <th className="px-3 py-2 text-left w-24">Tempo</th>
            <th className="px-3 py-2 text-left w-32">Genre</th>
            <th className="px-3 py-2 text-left w-28">Progress</th>
            <th className="px-3 py-2 text-left w-20">Tier</th>
            <th className="px-3 py-2 text-left w-16">Key</th>
            <th className="px-3 py-2 text-left w-40">Tags</th>
            <th className="px-3 py-2 text-left w-28">Created</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.id} className="border-b border-slate-800/60 hover:bg-slate-800/40">
              <td className="px-3 py-2 text-slate-400">{r.id}</td>
              <td className="px-3 py-2"><button className="h-7 w-7 grid place-items-center border border-slate-700 rounded text-slate-300 hover:bg-slate-700">⤢</button></td>
              <td className="px-3 py-2"><button className="h-7 w-7 grid place-items-center border border-slate-700 rounded text-slate-300 hover:bg-slate-700">▶</button></td>
              <td className="px-3 py-2">{r.name}</td>
              <td className="px-3 py-2">{r.tempo.toFixed(2)}</td>
              <td className="px-3 py-2 text-slate-400">{r.genre}</td>
              <td className="px-3 py-2 text-slate-400">{r.progress ?? ''}</td>
              <td className="px-3 py-2 text-slate-400">{r.tier}</td>
              <td className="px-3 py-2 text-slate-400">{r.key || <span className="text-slate-600">▾</span>}</td>
              <td className="px-3 py-2 text-slate-400">{(r.tags || []).join(', ')}</td>
              <td className="px-3 py-2 text-slate-400">{r.created}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
