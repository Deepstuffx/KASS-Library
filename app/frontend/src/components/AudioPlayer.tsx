import React, { useEffect, useRef, useState } from 'react'

export default function AudioPlayer({ src }: { src?: string }) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState(false)
  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(0)

  useEffect(() => {
    const a = audioRef.current
    if (!a) return
    const onTime = () => setTime(a.currentTime)
    const onLoaded = () => setDuration(a.duration || 0)
    a.addEventListener('timeupdate', onTime)
    a.addEventListener('loadedmetadata', onLoaded)
    return () => {
      a.removeEventListener('timeupdate', onTime)
      a.removeEventListener('loadedmetadata', onLoaded)
    }
  }, [src])

  useEffect(() => {
    const a = audioRef.current
    if (!a) return
    if (playing) a.play().catch(() => setPlaying(false))
    else a.pause()
  }, [playing])

  const toggle = () => setPlaying(p => !p)
  const seek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const a = audioRef.current
    if (!a) return
    const v = Number(e.target.value)
    a.currentTime = v
    setTime(v)
  }

  return (
    <div className="p-3 border rounded bg-white">
      <div className="text-sm font-semibold mb-2">Audio Player</div>
      <audio ref={audioRef} src={src} preload="metadata" />
      <div className="flex items-center space-x-2">
        <button className="px-3 py-1 bg-blue-600 text-white rounded disabled:opacity-50" onClick={toggle} disabled={!src}>
          {playing ? 'Pause' : 'Play'}
        </button>
        <input
          type="range"
          min={0}
          max={duration || 0}
          step={0.01}
          value={Math.min(time, duration || 0)}
          onChange={seek}
          className="flex-1"
          disabled={!src}
        />
        <div className="text-xs tabular-nums text-gray-600">{time.toFixed(1)} / {duration.toFixed(1)}s</div>
      </div>
    </div>
  )
}
