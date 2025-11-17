import React, { useState } from 'react'

const items = [
  { id: 'home', label: 'Home', icon: '🏠' },
  { id: 'folders', label: 'Folders', icon: '📁' },
  { id: 'projects', label: 'Projects', icon: '📂' },
  { id: 'files', label: 'Files', icon: '🗂' },
  { id: 'rules', label: 'Rules', icon: '⚙️' },
]

export default function LeftNav() {
  const [active, setActive] = useState('folders')
  return (
    <aside className="w-14 bg-[#0b1220] border-r border-slate-800 py-2 flex flex-col items-center gap-2">
      {items.map(it => (
        <button
          key={it.id}
          onClick={() => setActive(it.id)}
          title={it.label}
          className={
            'h-10 w-10 rounded grid place-items-center text-lg ' +
            (active === it.id ? 'bg-slate-800 text-white' : 'text-slate-300 hover:text-white hover:bg-slate-800')
          }
        >
          <span aria-hidden>{it.icon}</span>
        </button>
      ))}
    </aside>
  )
}
