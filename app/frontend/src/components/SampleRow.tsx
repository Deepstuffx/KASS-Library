import React from 'react';

export type SampleRowProps = {
  id: string;
  filename: string;
  bpm?: number | null;
  musicalKey?: string | null;
  tags?: string[];
  onSelect?: (id: string) => void;
};

export default function SampleRow({ id, filename, bpm, musicalKey, tags, onSelect }: SampleRowProps) {
  return (
    <tr className="hover:bg-gray-50 cursor-pointer" onClick={() => onSelect?.(id)}>
      <td className="px-3 py-2 text-sm">{filename}</td>
      <td className="px-3 py-2 text-sm">{bpm ?? ''}</td>
      <td className="px-3 py-2 text-sm">{musicalKey ?? ''}</td>
      <td className="px-3 py-2 text-sm">{(tags || []).slice(0,3).join(', ')}</td>
    </tr>
  );
}
