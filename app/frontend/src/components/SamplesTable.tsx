import React from 'react';
import SampleRow from './SampleRow';

type Sample = {
  id: string;
  filename: string;
  bpm?: number | null;
  key?: string | null;
  tags?: string[];
};

export default function SamplesTable({ samples, onSelect }: { samples: Sample[]; onSelect?: (id: string) => void }) {
  return (
    <div className="flex-1 overflow-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50 sticky top-0">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Filename</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">BPM</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Key</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Tags</th>
          </tr>
        </thead>
        <tbody className="bg-white">
          {samples.map((s) => (
            <SampleRow
              key={s.id}
              id={s.id}
              filename={s.filename}
              bpm={s.bpm}
              musicalKey={s.key}
              tags={s.tags}
              onSelect={onSelect}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
