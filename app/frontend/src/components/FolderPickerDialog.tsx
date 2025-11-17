import React from 'react';

export default function FolderPickerDialog({ open, onClose, onSelect }: { open: boolean; onClose: () => void; onSelect: (path: string) => void }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center">
      <div className="bg-white w-96 p-4 rounded shadow">
        <div className="mb-2 font-semibold">Select Folder</div>
        <div className="space-y-2">
          <input className="w-full border p-2 rounded" placeholder="/path/to/folder" />
          <div className="flex justify-end space-x-2">
            <button onClick={onClose} className="px-3 py-1">Cancel</button>
            <button onClick={() => { onSelect('/path/selected'); onClose(); }} className="px-3 py-1 bg-blue-600 text-white rounded">Select</button>
          </div>
        </div>
      </div>
    </div>
  );
}
