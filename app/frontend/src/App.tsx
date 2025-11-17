import React, { useState } from 'react'
import { TopBar, LeftNav, FolderTree } from './components'
import SamplesVirtualTable from './components/SamplesVirtualTable'
import ScanControl from './components/ScanControl'
import SamplesList from './components/SamplesList'
import RuleBuilderModal from './components/RuleBuilderModal'
import ExportPreview from './components/ExportPreview'

type Tab = 'Projects' | 'Scanner' | 'Rules' | 'Export' | 'Settings'

export default function App() {
  const [active, setActive] = useState<Tab>('Projects')
  const [ruleOpen, setRuleOpen] = useState(false)
  const [selectedSrc, setSelectedSrc] = useState<string | undefined>(undefined)

  return (
    <div className="h-screen w-screen bg-[#0b1220] text-slate-100 flex flex-col">
      <TopBar />
      <div className="flex-1 flex overflow-hidden">
        <LeftNav />
        <FolderTree />

        {/* Center content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Projects-like table view matching screenshot */}
          <div className="flex-1 flex flex-col">
            <div className="px-4 py-2 border-b border-slate-800 bg-[#0b1220] text-slate-300 text-sm">
              {(['Projects','Scanner','Rules','Export','Settings'] as Tab[]).map(t => (
                <button
                  key={t}
                  onClick={() => setActive(t)}
                  className={
                    'px-2 py-1 rounded mr-1 ' + (active === t ? 'bg-slate-800 text-white' : 'hover:bg-slate-800/70')
                  }
                >{t}</button>
              ))}
            </div>

            {active === 'Projects' && (
              <div className="flex-1 flex min-h-0">
                <SamplesVirtualTable />
              </div>
            )}

            {active === 'Scanner' && (
              <div className="p-4 overflow-auto"><ScanControl /></div>
            )}
            {active === 'Rules' && (
              <div className="p-4 overflow-auto">
                <div className="text-sm text-slate-400 mb-2">Define IF/THEN rules and priorities.</div>
                <div className="border border-slate-800 rounded bg-[#0f172a] p-4">No rules yet.</div>
                <div className="mt-3"><button className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded" onClick={() => setRuleOpen(true)}>New Rule</button></div>
                <RuleBuilderModal open={ruleOpen} onClose={() => setRuleOpen(false)} />
              </div>
            )}
            {active === 'Export' && (
              <div className="p-4 overflow-auto"><ExportPreview /></div>
            )}
            {active === 'Settings' && (
              <div className="p-4 overflow-auto"><div className="border border-slate-800 rounded bg-[#0f172a] p-4">Settings go here.</div></div>
            )}
          </div>
        </main>

        {/* Floating add button bottom-right like screenshot */}
        <div className="absolute right-4 bottom-4">
          <button className="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-100 rounded shadow border border-slate-600 text-sm">+ Add Projects</button>
        </div>
      </div>
    </div>
  )
}
