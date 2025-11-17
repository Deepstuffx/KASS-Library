import { convertFileSrc } from '@tauri-apps/api/core'

export function fileUrl(absPath?: string | null): string {
  if (!absPath) return ''
  try {
    return convertFileSrc(absPath)
  } catch {
    // Fallback for non-tauri environments (browser dev)
    return `file://${absPath}`
  }
}
