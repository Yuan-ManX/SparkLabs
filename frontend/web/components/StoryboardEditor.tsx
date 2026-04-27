import React, { useState } from 'react';
import { Layout, Plus, Trash2, Image, Film } from 'lucide-react';

interface StoryboardFrame {
  id: string;
  description: string;
  duration: number;
  cameraAngle: string;
}

const StoryboardEditor: React.FC = () => {
  const [frames, setFrames] = useState<StoryboardFrame[]>([]);
  const [selectedFrame, setSelectedFrame] = useState<string | null>(null);
  const [newDesc, setNewDesc] = useState('');

  const addFrame = () => {
    if (!newDesc.trim()) return;
    const frame: StoryboardFrame = {
      id: `frame_${Date.now()}`,
      description: newDesc,
      duration: 3,
      cameraAngle: 'medium',
    };
    setFrames([...frames, frame]);
    setNewDesc('');
  };

  const removeFrame = (id: string) => {
    setFrames(frames.filter((f) => f.id !== id));
    if (selectedFrame === id) setSelectedFrame(null);
  };

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Layout className="w-8 h-8 text-orange-400" />
          <h1 className="text-2xl font-bold">Storyboard Editor</h1>
        </div>

        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 mb-6">
          <div className="flex gap-3">
            <input
              type="text"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addFrame()}
              placeholder="Describe the scene frame..."
              className="flex-1 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm"
            />
            <button onClick={addFrame} className="px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg text-sm font-medium flex items-center gap-2">
              <Plus className="w-4 h-4" />
              Add Frame
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {frames.map((frame, index) => (
            <div
              key={frame.id}
              onClick={() => setSelectedFrame(frame.id)}
              className={`bg-slate-800/50 border rounded-xl overflow-hidden cursor-pointer transition-all ${
                selectedFrame === frame.id ? 'border-orange-500 ring-1 ring-orange-500/30' : 'border-slate-700 hover:border-slate-600'
              }`}
            >
              <div className="aspect-video bg-slate-700/50 flex items-center justify-center relative">
                <Film className="w-8 h-8 text-slate-500" />
                <span className="absolute top-2 left-2 text-xs bg-black/50 px-2 py-0.5 rounded">
                  Frame {index + 1}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); removeFrame(frame.id); }}
                  className="absolute top-2 right-2 p-1 bg-black/50 hover:bg-red-600 rounded"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
              <div className="p-3">
                <p className="text-sm text-slate-300 line-clamp-2">{frame.description}</p>
                <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
                  <span>{frame.duration}s</span>
                  <span>|</span>
                  <span>{frame.cameraAngle}</span>
                </div>
              </div>
            </div>
          ))}
          {frames.length === 0 && (
            <div className="col-span-full text-center py-20 text-slate-500">
              <Layout className="w-16 h-16 mx-auto mb-4 text-slate-600" />
              <p className="text-lg font-medium">Storyboard Editor</p>
              <p className="text-sm mt-1">Add frames to design your cinematic sequences</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StoryboardEditor;
