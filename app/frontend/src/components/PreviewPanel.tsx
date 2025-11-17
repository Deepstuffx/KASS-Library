import React from 'react';

export default function PreviewPanel({ children }: { children?: React.ReactNode }) {
  return (
    <aside className="w-96 bg-white border-l border-gray-200 p-4 flex flex-col">
      <div className="mb-2 text-sm font-semibold">Preview</div>
      <div className="flex-1 overflow-auto">{children ?? <div className="text-gray-500">Select a sample to preview</div>}</div>
    </aside>
  );
}
