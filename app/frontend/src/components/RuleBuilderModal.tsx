import React from 'react';

export default function RuleBuilderModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center">
      <div className="bg-white w-3/4 max-w-2xl p-6 rounded shadow">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Rule Builder</h3>
          <button onClick={onClose} className="text-gray-600 hover:text-black">Close</button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">When</label>
            <input className="mt-1 block w-full border rounded p-2" placeholder="filename contains 'loop'" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Then</label>
            <select className="mt-1 block w-full border rounded p-2">
              <option>Move to Loops</option>
              <option>Move to Drums</option>
              <option>Move to Vocals</option>
            </select>
          </div>
          <div className="flex justify-end">
            <button className="px-4 py-2 bg-blue-600 text-white rounded">Save Rule</button>
          </div>
        </div>
      </div>
    </div>
  );
}
