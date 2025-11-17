import React from 'react';

export default function ExportPreview({ moves }: { moves?: Array<{src:string; dst:string}> }) {
  return (
    <div className="p-4">
      <h4 className="font-semibold mb-2">Export Preview</h4>
      <div className="overflow-auto max-h-64 border rounded bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              <th className="px-2 py-1 text-left">Source</th>
              <th className="px-2 py-1 text-left">Destination</th>
            </tr>
          </thead>
          <tbody>
            {(moves || []).map((m, i) => (
              <tr key={i} className="odd:bg-white even:bg-gray-50">
                <td className="px-2 py-1">{m.src}</td>
                <td className="px-2 py-1">{m.dst}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
