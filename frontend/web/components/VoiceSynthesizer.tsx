import React, { useState } from 'react';
import { Music, Play, Volume2 } from 'lucide-react';

const VoiceSynthesizer: React.FC = () => {
  const [text, setText] = useState('');
  const [voice, setVoice] = useState('female_1');
  const [speed, setSpeed] = useState(1.0);
  const [pitch, setPitch] = useState(1.0);

  const voices = [
    { id: 'female_1', name: 'Female - Soft', color: 'bg-pink-500/20 text-pink-400' },
    { id: 'female_2', name: 'Female - Strong', color: 'bg-rose-500/20 text-rose-400' },
    { id: 'male_1', name: 'Male - Deep', color: 'bg-blue-500/20 text-blue-400' },
    { id: 'male_2', name: 'Male - Warm', color: 'bg-indigo-500/20 text-indigo-400' },
    { id: 'neutral', name: 'Neutral - AI', color: 'bg-violet-500/20 text-violet-400' },
    { id: 'robot', name: 'Robot - Mechanical', color: 'bg-cyan-500/20 text-cyan-400' },
  ];

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Music className="w-8 h-8 text-green-400" />
          <h1 className="text-2xl font-bold">Voice Synthesizer</h1>
        </div>

        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 mb-6">
          <div className="space-y-4">
            <div>
              <label className="text-sm text-slate-400 block mb-2">Text to Synthesize</label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={4}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-sm resize-none"
                placeholder="Enter dialogue text for voice synthesis..."
              />
            </div>

            <div>
              <label className="text-sm text-slate-400 block mb-2">Voice Character</label>
              <div className="grid grid-cols-3 gap-2">
                {voices.map((v) => (
                  <button
                    key={v.id}
                    onClick={() => setVoice(v.id)}
                    className={`px-3 py-2 rounded-lg text-sm font-medium border transition-all ${
                      voice === v.id ? `${v.color} border-current` : 'bg-slate-700 border-slate-600 text-slate-300'
                    }`}
                  >
                    {v.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-slate-400 block mb-2">Speed: {speed.toFixed(1)}x</label>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={speed}
                  onChange={(e) => setSpeed(parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>
              <div>
                <label className="text-sm text-slate-400 block mb-2">Pitch: {pitch.toFixed(1)}</label>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={pitch}
                  onChange={(e) => setPitch(parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>

            <button className="w-full px-4 py-3 bg-green-600 hover:bg-green-700 rounded-lg font-medium flex items-center justify-center gap-2">
              <Volume2 className="w-4 h-4" />
              Synthesize Voice
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VoiceSynthesizer;
