import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

const PlatformLayerPanel: React.FC = () => {
  const [capabilities, setCapabilities] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [backendCompat, setBackendCompat] = useState<any>(null);
  const [platform, setPlatform] = useState<string>('');

  const fetchData = useCallback(async () => {
    try {
      const [capsRes, statsRes, backendRes] = await Promise.all([
        fetch(`${API_BASE}/platform-layer/capabilities`).then(r => r.json()),
        fetch(`${API_BASE}/platform-layer/stats`).then(r => r.json()),
        fetch(`${API_BASE}/platform-layer/backend-compatibility`).then(r => r.json()),
      ]);
      setCapabilities(capsRes);
      setStats(statsRes);
      setBackendCompat(backendRes);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleDetect = async () => {
    try {
      const res = await fetch(`${API_BASE}/platform-layer/detect`, { method: 'POST' });
      const data = await res.json();
      setPlatform(data.platform || '');
      fetchData();
    } catch {}
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">🖥️</span>
          <span className="text-[12px] font-semibold text-[#ccc]">Platform Layer</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleDetect} className="text-[9px] px-2 py-1 bg-orange-600 hover:bg-orange-500 text-white rounded">
            Detect Platform
          </button>
          <button onClick={fetchData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
            Refresh
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Platform Info */}
        {(platform || capabilities) && (
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-blue-400 capitalize">
                {platform || capabilities?.platform || 'Unknown'}
              </div>
              <div className="text-[9px] text-[#666]">Target Platform</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-green-400 capitalize">
                {capabilities?.preferred_backend || 'N/A'}
              </div>
              <div className="text-[9px] text-[#666]">Render Backend</div>
            </div>
          </div>
        )}

        {/* Capabilities */}
        {capabilities && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
            <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Capabilities</h4>
            <div className="space-y-1.5">
              {Object.entries(capabilities).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between text-[10px] p-1.5 bg-[#111] rounded">
                  <span className="text-[#888] capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className="text-[#aaa]">
                    {typeof value === 'boolean' ? (
                      <span className={value ? 'text-green-400' : 'text-red-400'}>
                        {value ? 'Yes' : 'No'}
                      </span>
                    ) : typeof value === 'object' ? JSON.stringify(value) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Platform Stats */}
        {stats && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
            <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Platform Stats</h4>
            <div className="space-y-1.5">
              {Object.entries(stats).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between text-[10px] p-1.5 bg-[#111] rounded">
                  <span className="text-[#888] capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className="text-[#aaa]">
                    {typeof value === 'number' ? value.toFixed(1) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Backend Compatibility */}
        {backendCompat && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
            <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Backend Compatibility</h4>
            <div className="space-y-1">
              {Array.isArray(backendCompat)
                ? backendCompat.map((item: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-1.5 bg-[#111] rounded text-[10px]">
                      <span className="text-[#888] capitalize">{item.backend || item.name || `Backend ${i}`}</span>
                      <span className={item.supported ? 'text-green-400' : 'text-red-400'}>
                        {item.supported ? 'Supported' : 'Not Supported'}
                      </span>
                    </div>
                  ))
                : Object.entries(backendCompat).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between p-1.5 bg-[#111] rounded text-[10px]">
                      <span className="text-[#888] capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className="text-[#aaa]">
                        {typeof value === 'boolean' ? (
                          <span className={value ? 'text-green-400' : 'text-red-400'}>
                            {value ? 'Supported' : 'Not Supported'}
                          </span>
                        ) : String(value)}
                      </span>
                    </div>
                  ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PlatformLayerPanel;