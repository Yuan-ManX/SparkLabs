import React, { useState } from 'react';
import { Film, Play, Settings } from 'lucide-react';

const VideoRenderer: React.FC = () => {
  const [resolution, setResolution] = useState('1080p');
  const [fps, setFps] = useState(30);
  const [format, setFormat] = useState('mp4');
  const [rendering, setRendering] = useState(false);

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Film className="w-8 h-8 text-pink-400" />
          <h1 className="text-2xl font-bold">Video Renderer</h1>
        </div>

        <div className="bg-[#0f0f0f]/50 border border-[#1e1e1e] rounded-xl p-6 mb-6">
          <h3 className="font-bold mb-4">Render Settings</h3>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div>
              <label className="text-sm text-[#999] block mb-2">Resolution</label>
              <select
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                className="w-full px-3 py-2 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-sm"
              >
                <option value="720p">720p</option>
                <option value="1080p">1080p</option>
                <option value="2k">2K</option>
                <option value="4k">4K</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-[#999] block mb-2">Frame Rate</label>
              <select
                value={fps}
                onChange={(e) => setFps(parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-sm"
              >
                <option value={24}>24 FPS</option>
                <option value={30}>30 FPS</option>
                <option value={60}>60 FPS</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-[#999] block mb-2">Format</label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value)}
                className="w-full px-3 py-2 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-sm"
              >
                <option value="mp4">MP4</option>
                <option value="webm">WebM</option>
                <option value="gif">GIF</option>
              </select>
            </div>
          </div>

          <button
            onClick={() => setRendering(!rendering)}
            className={`w-full px-4 py-3 rounded-lg font-medium flex items-center justify-center gap-2 ${
              rendering ? 'bg-red-600 hover:bg-red-700' : 'bg-pink-600 hover:bg-pink-700'
            }`}
          >
            {rendering ? (
              <>
                <Settings className="w-4 h-4 animate-spin" />
                Cancel Rendering
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Start Rendering
              </>
            )}
          </button>
        </div>

        <div className="bg-[#0f0f0f]/50 border border-[#1e1e1e] rounded-xl p-6">
          <h3 className="font-bold mb-4">Preview</h3>
          <div className="aspect-video bg-[#1a1a1a]/50 rounded-lg flex items-center justify-center border border-[#2a2a2a] border-dashed">
            <div className="text-center text-[#999]">
              <Film className="w-12 h-12 mx-auto mb-2 text-[#666]" />
              <p className="text-sm">Video preview will appear here</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoRenderer;
