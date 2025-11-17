import React from 'react'

export default function TopBar() {
  const buildTime = (typeof __BUILD_TIME__ !== 'undefined' && __BUILD_TIME__) || ''
  const gitSha = (typeof __GIT_SHA__ !== 'undefined' && __GIT_SHA__) || ''
  const mode = import.meta.env.DEV ? 'DEV' : 'PROD'
  const timeLabel = buildTime ? new Date(buildTime).toLocaleString() : ''
  return (
    <header className="h-12 w-full bg-[#0f172a] border-b border-slate-800 flex items-center px-3 select-none">
      <div className="font-semibold text-slate-200 tracking-wide mr-4">KASS</div>
      <div className="hidden md:flex items-center text-xs text-slate-400 mr-4">
        <span className="px-1.5 py-0.5 rounded bg-slate-800/70 border border-slate-700">
          {mode}{gitSha ? ` • ${gitSha}` : ''}{timeLabel ? ` • ${timeLabel}` : ''}
        </span>
      </div>
      <div className="flex-1">
        <div className="relative max-w-xl">
          <input
            className="w-full bg-slate-800/60 text-slate-200 placeholder-slate-400 px-3 py-1 rounded outline-none border border-slate-700 focus:border-slate-500"
            placeholder="Search your projects…  ⌘F"
          />
          <div className="absolute right-2 top-1.5 text-slate-400 text-xs">⌘F</div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {['↻','▦','▤','⦿','☁','👤','🎁','⚙'].map((sym, i) => (
          <button key={i} className="h-8 w-8 grid place-items-center text-slate-300 hover:text-white hover:bg-slate-800 rounded">
            <span className="text-sm" aria-hidden>{sym}</span>
          </button>
        ))}
      </div>
    </header>
  )
}
