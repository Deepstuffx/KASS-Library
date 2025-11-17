import React, { useState } from 'react'

type Node = { id: string; name: string; children?: Node[] }

const demoTree: Node[] = [
  {
    id: 'projects',
    name: 'projects',
    children: [
      {
        id: 'funny',
        name: 'FUcking eww',
        children: [
          { id: 'live', name: 'Live Temps', children: [ { id: 'mac2025', name: 'MAC 2025' } ] },
          { id: 'proj2025', name: 'Proj 2025' },
        ],
      },
    ],
  },
]

function Row({ node, depth, selected, onSelect }: { node: Node; depth: number; selected?: string; onSelect: (id: string) => void }) {
  const [open, setOpen] = useState(true)
  const hasChildren = !!node.children?.length
  return (
    <div className="text-slate-300">
      <div
        className={
          'flex items-center gap-2 px-2 py-1 rounded cursor-pointer ' +
          (selected === node.id ? 'bg-slate-700 text-white' : 'hover:bg-slate-800')
        }
        style={{ paddingLeft: depth * 12 + 8 }}
        onClick={() => (hasChildren ? setOpen(o => !o) : onSelect(node.id))}
      >
        {hasChildren ? <span className="text-xs">{open ? '▾' : '▸'}</span> : <span className="text-xs">📁</span>}
        <span className="truncate">{node.name}</span>
      </div>
      {hasChildren && open && (
        <div>
          {node.children!.map(ch => (
            <Row key={ch.id} node={ch} depth={depth + 1} onSelect={onSelect} selected={selected} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function FolderTree() {
  const [sel, setSel] = useState('mac2025')
  return (
    <aside className="w-64 bg-[#0f172a] border-r border-slate-800 p-2 overflow-auto">
      <div className="text-slate-400 text-xs uppercase px-2 mb-2">Folders</div>
      {demoTree.map(n => (
        <Row key={n.id} node={n} depth={0} onSelect={setSel} selected={sel} />
      ))}
    </aside>
  )
}
