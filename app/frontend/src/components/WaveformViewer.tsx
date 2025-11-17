import React, { useEffect, useRef, useState } from 'react'

// Lightweight, lazy wavesurfer integration to keep initial bundle small.
// Only loads the library when a source is provided and the element is visible.
export default function WaveformViewer({ src }: { src?: string }) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const waveRef = useRef<any>(null)
  const [visible, setVisible] = useState(false)

  // Observe visibility to avoid initializing when offscreen
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting) setVisible(true)
      }
    }, { root: null, threshold: 0.1 })
    io.observe(el)
    return () => io.disconnect()
  }, [])

  useEffect(() => {
    let cancelled = false
    async function init() {
      if (!src || !visible || !containerRef.current) return
      try {
        const mod = await import('wavesurfer.js')
        if (cancelled) return
        const WaveSurfer = mod.default || (mod as any)
        // Destroy any prior instance before creating a new one
        if (waveRef.current) {
          try { waveRef.current.destroy(); } catch {}
          waveRef.current = null
        }
        waveRef.current = WaveSurfer.create({
          container: containerRef.current,
          waveColor: '#94a3b8',
          progressColor: '#38bdf8',
          cursorColor: '#cbd5e1',
          height: 64,
          interact: true,
          autoCenter: true,
          barWidth: 2,
          barRadius: 2,
          barGap: 1,
        })
        waveRef.current.load(src)
      } catch (e) {
        // Render a placeholder on failure
        if (containerRef.current) {
          containerRef.current.innerHTML = '<div class="h-16 bg-slate-700/50 rounded"></div>'
        }
      }
    }
    init()
    return () => { cancelled = true }
  }, [src, visible])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (waveRef.current) {
        try { waveRef.current.destroy() } catch {}
        waveRef.current = null
      }
    }
  }, [])

  if (!src) {
    return <div className="text-gray-400 text-sm">No waveform</div>
  }
  return <div className="w-full" ref={containerRef} />
}
