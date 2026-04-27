import React, { useState } from 'react';
import { Image, Sparkles, Download } from 'lucide-react';

const AssetGenerator: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [assetType, setAssetType] = useState('image');
  const [style, setStyle] = useState('realistic');
  const [generated, setGenerated] = useState(false);

  const handleGenerate = () => {
    if (!prompt.trim()) return;
    setGenerated(true);
  };

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Image className="w-8 h-8 text-purple-400" />
          <h1 className="text-2xl font-bold">AI Asset Generator</h1>
        </div>

        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 mb-6">
          <div className="space-y-4">
            <div>
              <label className="text-sm text-slate-400 block mb-2">Prompt</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={3}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-sm resize-none"
                placeholder="Describe the asset you want to generate..."
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-slate-400 block mb-2">Asset Type</label>
                <select
                  value={assetType}
                  onChange={(e) => setAssetType(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm"
                >
                  <option value="image">Image</option>
                  <option value="texture">Texture</option>
                  <option value="sprite">Sprite Sheet</option>
                  <option value="icon">Icon</option>
                  <option value="background">Background</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-slate-400 block mb-2">Style</label>
                <select
                  value={style}
                  onChange={(e) => setStyle(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm"
                >
                  <option value="realistic">Realistic</option>
                  <option value="anime">Anime</option>
                  <option value="pixel">Pixel Art</option>
                  <option value="watercolor">Watercolor</option>
                  <option value="lowpoly">Low Poly</option>
                </select>
              </div>
            </div>
            <button
              onClick={handleGenerate}
              className="w-full px-4 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-medium flex items-center justify-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              Generate Asset
            </button>
          </div>
        </div>

        {generated && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold">Generated Asset</h3>
              <button className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-sm flex items-center gap-2">
                <Download className="w-4 h-4" />
                Download
              </button>
            </div>
            <div className="aspect-video bg-slate-700/50 rounded-lg flex items-center justify-center border border-slate-600 border-dashed">
              <div className="text-center text-slate-400">
                <Image className="w-12 h-12 mx-auto mb-2 text-slate-500" />
                <p className="text-sm">Connect to the engine for AI asset generation</p>
                <p className="text-xs mt-1 text-slate-500">Prompt: "{prompt}"</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AssetGenerator;
