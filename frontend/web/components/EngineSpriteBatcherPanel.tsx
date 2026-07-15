import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

// Types for the Sprite Batcher API responses and forms

interface BatcherStatus {
  command_count: number;
  batch_count: number;
  atlas_count: number;
  draw_calls_saved: number;
  gpu_memory: number;
}

interface SubmitResult {
  command_id: string;
  texture_name: string;
  batched: boolean;
}

interface BatchInfo {
  batch_id: string;
  vertex_count: number;
  index_count: number;
  gpu_memory_estimate: number;
  draw_call_count: number;
}

interface FlushResult {
  batches: BatchInfo[];
  total_vertices: number;
  total_indices: number;
  total_gpu_memory_estimate: number;
}

interface TextureAtlas {
  id: string;
  name: string;
  texture_names: string[];
  size: number;
  pack_mode: string;
  texture_count: number;
}

interface AtlasesResult {
  atlases: TextureAtlas[];
}

interface FrameReport {
  frame_number: number;
  frame_draw_calls: number;
  frame_batch_count: number;
  commands_processed: number;
}

interface AtlasForm {
  name: string;
  textureNames: string;
  size: number;
  packMode: string;
}

interface SubmitForm {
  textureName: string;
  positionX: number;
  positionY: number;
  scaleX: number;
  scaleY: number;
  rotationDegrees: number;
  colorR: number;
  colorG: number;
  colorB: number;
  colorA: number;
  blendMode: string;
  zOrder: number;
}

const EngineSpriteBatcherPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('status');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  // Status tab
  const [status, setStatus] = useState<BatcherStatus | null>(null);

  // Submit tab
  const [submitForm, setSubmitForm] = useState<SubmitForm>({
    textureName: '',
    positionX: 0,
    positionY: 0,
    scaleX: 1,
    scaleY: 1,
    rotationDegrees: 0,
    colorR: 255,
    colorG: 255,
    colorB: 255,
    colorA: 255,
    blendMode: 'normal',
    zOrder: 0,
  });

  // Flush tab
  const [flushResult, setFlushResult] = useState<FlushResult | null>(null);

  // Atlases tab
  const [atlases, setAtlases] = useState<TextureAtlas[]>([]);
  const [atlasForm, setAtlasForm] = useState<AtlasForm>({
    name: '',
    textureNames: '',
    size: 2048,
    packMode: 'bin_pack',
  });

  // Frame Report tab
  const [frameReport, setFrameReport] = useState<FrameReport | null>(null);

  const apiBase = API_ROOT + '/engine';

  const tabs = [
    { id: 'status', label: 'Status' },
    { id: 'submit', label: 'Submit' },
    { id: 'flush', label: 'Flush' },
    { id: 'atlases', label: 'Atlases' },
    { id: 'frame-report', label: 'Frame Report' },
  ];

  // Fetch status data
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/sprite-batcher/status`);
      if (!res.ok) throw new Error('Failed to fetch sprite batcher status');
      const json: BatcherStatus = await res.json();
      setStatus(json);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch status');
    }
  }, []);

  // Fetch atlases
  const fetchAtlases = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/sprite-batcher/atlases`);
      if (!res.ok) throw new Error('Failed to fetch atlases');
      const json: AtlasesResult = await res.json();
      setAtlases(json.atlases || []);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch atlases');
    }
  }, []);

  // Fetch frame report
  const fetchFrameReport = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/sprite-batcher/frame-report`);
      if (!res.ok) throw new Error('Failed to fetch frame report');
      const json: FrameReport = await res.json();
      setFrameReport(json);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch frame report');
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchAtlases();
    fetchFrameReport();
    const i = setInterval(() => {
      fetchStatus();
      fetchAtlases();
      fetchFrameReport();
    }, 15000);
    return () => clearInterval(i);
  }, [fetchStatus, fetchAtlases, fetchFrameReport]);

  const handleSubmitCommand = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${apiBase}/sprite-batcher/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          texture_name: submitForm.textureName,
          position_x: submitForm.positionX,
          position_y: submitForm.positionY,
          scale_x: submitForm.scaleX,
          scale_y: submitForm.scaleY,
          rotation_degrees: submitForm.rotationDegrees,
          color_rgba: [submitForm.colorR, submitForm.colorG, submitForm.colorB, submitForm.colorA],
          blend_mode: submitForm.blendMode,
          z_order: submitForm.zOrder,
        }),
      });
      if (!res.ok) throw new Error('Failed to submit command');
      const json: SubmitResult = await res.json();
      setResult(json);
    } catch (err: any) {
      setError(err.message || 'Failed to submit command');
    } finally {
      setLoading(false);
    }
  };

  const handleFlush = async () => {
    setLoading(true);
    setError(null);
    setFlushResult(null);
    try {
      const res = await fetch(`${apiBase}/sprite-batcher/flush`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error('Failed to flush batches');
      const json: FlushResult = await res.json();
      setFlushResult(json);
    } catch (err: any) {
      setError(err.message || 'Failed to flush batches');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/sprite-batcher/clear`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error('Failed to clear frame buffer');
      setFlushResult(null);
      setResult(null);
    } catch (err: any) {
      setError(err.message || 'Failed to clear frame buffer');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAtlas = async () => {
    if (!atlasForm.name.trim()) {
      setError('Please enter an atlas name');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const textureNames = atlasForm.textureNames
        .split(',')
        .map(s => s.trim())
        .filter(s => s.length > 0);
      const res = await fetch(`${apiBase}/sprite-batcher/create-atlas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: atlasForm.name,
          texture_names: textureNames,
          size: atlasForm.size,
          pack_mode: atlasForm.packMode,
        }),
      });
      if (!res.ok) throw new Error('Failed to create atlas');
      const json = await res.json();
      setResult(json);
      setAtlasForm({ name: '', textureNames: '', size: 2048, packMode: 'bin_pack' });
      fetchAtlases();
    } catch (err: any) {
      setError(err.message || 'Failed to create atlas');
    } finally {
      setLoading(false);
    }
  };

  const formatMemory = (bytes: number): string => {
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${bytes} B`;
  };

  const renderTab = () => {
    switch (activeTab) {
      case 'status':
        return renderStatusTab();
      case 'submit':
        return renderSubmitTab();
      case 'flush':
        return renderFlushTab();
      case 'atlases':
        return renderAtlasesTab();
      case 'frame-report':
        return renderFrameReportTab();
      default:
        return null;
    }
  };

  const renderStatusTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Sprite Batcher System Status</div>

      {status ? (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-[#999] text-xs">Command Count</div>
            <div className="text-white text-sm font-mono">{status.command_count}</div>
          </div>
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-[#999] text-xs">Batch Count</div>
            <div className="text-white text-sm font-mono">{status.batch_count}</div>
          </div>
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-[#999] text-xs">Atlas Count</div>
            <div className="text-white text-sm font-mono">{status.atlas_count}</div>
          </div>
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-[#999] text-xs">Draw Calls Saved</div>
            <div className="text-white text-sm font-mono">{status.draw_calls_saved}</div>
          </div>
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center col-span-2">
            <div className="text-[#999] text-xs">GPU Memory</div>
            <div className="text-white text-sm font-mono">{formatMemory(status.gpu_memory)}</div>
          </div>
        </div>
      ) : (
        <div className="text-[#999] text-sm">No status data available.</div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  const renderSubmitTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Submit Sprite Draw Command</div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="grid grid-cols-2 gap-3">
          {/* Texture Name */}
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Texture Name</label>
            <input
              type="text"
              value={submitForm.textureName}
              onChange={e => setSubmitForm(prev => ({ ...prev, textureName: e.target.value }))}
              placeholder="e.g. player_sprite.png"
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>

          {/* Position */}
          <div>
            <label className="text-xs text-[#999] mb-1 block">Position X</label>
            <input
              type="number"
              value={submitForm.positionX}
              onChange={e => setSubmitForm(prev => ({ ...prev, positionX: parseFloat(e.target.value) || 0 }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Position Y</label>
            <input
              type="number"
              value={submitForm.positionY}
              onChange={e => setSubmitForm(prev => ({ ...prev, positionY: parseFloat(e.target.value) || 0 }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>

          {/* Scale */}
          <div>
            <label className="text-xs text-[#999] mb-1 block">Scale X</label>
            <input
              type="number"
              value={submitForm.scaleX}
              onChange={e => setSubmitForm(prev => ({ ...prev, scaleX: parseFloat(e.target.value) || 1 }))}
              step="0.1"
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Scale Y</label>
            <input
              type="number"
              value={submitForm.scaleY}
              onChange={e => setSubmitForm(prev => ({ ...prev, scaleY: parseFloat(e.target.value) || 1 }))}
              step="0.1"
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>

          {/* Rotation */}
          <div>
            <label className="text-xs text-[#999] mb-1 block">Rotation (degrees)</label>
            <input
              type="number"
              value={submitForm.rotationDegrees}
              onChange={e => setSubmitForm(prev => ({ ...prev, rotationDegrees: parseFloat(e.target.value) || 0 }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>

          {/* Z-Order */}
          <div>
            <label className="text-xs text-[#999] mb-1 block">Z-Order</label>
            <input
              type="number"
              value={submitForm.zOrder}
              onChange={e => setSubmitForm(prev => ({ ...prev, zOrder: parseInt(e.target.value, 10) || 0 }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>

          {/* Color RGBA */}
          <div>
            <label className="text-xs text-[#999] mb-1 block">Color R</label>
            <input
              type="number"
              min={0}
              max={255}
              value={submitForm.colorR}
              onChange={e => setSubmitForm(prev => ({ ...prev, colorR: parseInt(e.target.value, 10) || 0 }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Color G</label>
            <input
              type="number"
              min={0}
              max={255}
              value={submitForm.colorG}
              onChange={e => setSubmitForm(prev => ({ ...prev, colorG: parseInt(e.target.value, 10) || 0 }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Color B</label>
            <input
              type="number"
              min={0}
              max={255}
              value={submitForm.colorB}
              onChange={e => setSubmitForm(prev => ({ ...prev, colorB: parseInt(e.target.value, 10) || 0 }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Color A</label>
            <input
              type="number"
              min={0}
              max={255}
              value={submitForm.colorA}
              onChange={e => setSubmitForm(prev => ({ ...prev, colorA: parseInt(e.target.value, 10) || 0 }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>

          {/* Blend Mode */}
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Blend Mode</label>
            <select
              value={submitForm.blendMode}
              onChange={e => setSubmitForm(prev => ({ ...prev, blendMode: e.target.value }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="normal">Normal</option>
              <option value="additive">Additive</option>
              <option value="multiply">Multiply</option>
              <option value="alpha">Alpha</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleSubmitCommand}
          disabled={loading}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] mt-4"
        >
          {loading ? 'Submitting...' : 'Submit Command'}
        </button>
      </div>

      {result && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">
            {JSON.stringify(result, null, 2)}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  const renderFlushTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Flush & Clear Operations</div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="flex gap-3">
          <button
            onClick={handleFlush}
            disabled={loading}
            className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
          >
            {loading ? 'Flushing...' : 'Flush Batches'}
          </button>
          <button
            onClick={handleClear}
            disabled={loading}
            className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
          >
            {loading ? 'Clearing...' : 'Clear Frame Buffer'}
          </button>
        </div>
        <p className="text-[#999] text-xs mt-2">
          Flush sends all batched commands to the GPU. Clear empties the frame buffer without rendering.
        </p>
      </div>

      {flushResult && (
        <div className="flex flex-col gap-3">
          <div className="text-sm font-medium text-[#00d4ff]">Batches</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
              <div className="text-[#999] text-xs">Total Vertices</div>
              <div className="text-white text-sm font-mono">{flushResult.total_vertices}</div>
            </div>
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
              <div className="text-[#999] text-xs">Total Indices</div>
              <div className="text-white text-sm font-mono">{flushResult.total_indices}</div>
            </div>
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center col-span-2">
              <div className="text-[#999] text-xs">Total GPU Memory Estimate</div>
              <div className="text-white text-sm font-mono">{formatMemory(flushResult.total_gpu_memory_estimate)}</div>
            </div>
          </div>

          {flushResult.batches && flushResult.batches.length > 0 && (
            <div>
              <div className="text-sm font-medium text-[#00d4ff] mb-2">Batch Details</div>
              {flushResult.batches.map((batch, i) => (
                <div key={batch.batch_id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
                  <div className="text-xs text-[#999] mb-2">Batch ID: {batch.batch_id}</div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-[#999] text-xs">Vertices</div>
                      <div className="text-white text-sm font-mono">{batch.vertex_count}</div>
                    </div>
                    <div>
                      <div className="text-[#999] text-xs">Indices</div>
                      <div className="text-white text-sm font-mono">{batch.index_count}</div>
                    </div>
                    <div>
                      <div className="text-[#999] text-xs">Draw Calls</div>
                      <div className="text-white text-sm font-mono">{batch.draw_call_count}</div>
                    </div>
                    <div>
                      <div className="text-[#999] text-xs">GPU Memory</div>
                      <div className="text-white text-sm font-mono">{formatMemory(batch.gpu_memory_estimate)}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  const renderAtlasesTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Create Texture Atlas</div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Name</label>
            <input
              type="text"
              value={atlasForm.name}
              onChange={e => setAtlasForm(prev => ({ ...prev, name: e.target.value }))}
              placeholder="e.g. MainAtlas"
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Size</label>
            <input
              type="number"
              value={atlasForm.size}
              onChange={e => setAtlasForm(prev => ({ ...prev, size: parseInt(e.target.value, 10) || 2048 }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Pack Mode</label>
            <select
              value={atlasForm.packMode}
              onChange={e => setAtlasForm(prev => ({ ...prev, packMode: e.target.value }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="bin_pack">Bin Pack</option>
              <option value="row_strip">Row Strip</option>
            </select>
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Texture Names (comma-separated)</label>
            <textarea
              value={atlasForm.textureNames}
              onChange={e => setAtlasForm(prev => ({ ...prev, textureNames: e.target.value }))}
              placeholder="sprite1.png, sprite2.png, sprite3.png"
              rows={3}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleCreateAtlas}
          disabled={loading}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] mt-4"
        >
          {loading ? 'Creating...' : 'Create Atlas'}
        </button>
      </div>

      <div className="text-sm font-medium text-[#00d4ff] mb-2">Existing Atlases</div>

      {atlases.length > 0 ? (
        atlases.map((atlas, i) => (
          <div key={atlas.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
            <div className="flex justify-between items-center mb-2">
              <div className="text-white text-sm font-medium">{atlas.name}</div>
              <div className="text-[#999] text-xs">
                {atlas.texture_count || (atlas.texture_names?.length || 0)} textures
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-[#999] text-xs">Size</div>
                <div className="text-white text-sm font-mono">{atlas.size}px</div>
              </div>
              <div>
                <div className="text-[#999] text-xs">Pack Mode</div>
                <div className="text-white text-sm font-mono">{atlas.pack_mode}</div>
              </div>
            </div>
            {atlas.texture_names && atlas.texture_names.length > 0 && (
              <div className="mt-2">
                <div className="text-[#999] text-xs mb-1">Textures</div>
                <div className="flex flex-wrap gap-1">
                  {atlas.texture_names.map((name, j) => (
                    <span key={j} className="bg-[#0f0f23] border border-[#2a2a4a] rounded px-2 py-1 text-xs text-[#ccc] font-mono">
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))
      ) : (
        <div className="text-[#999] text-sm">No atlases created yet.</div>
      )}

      {result && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">
            {JSON.stringify(result, null, 2)}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  const renderFrameReportTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Current Frame Batch Report</div>

      {frameReport ? (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-[#999] text-xs">Frame Number</div>
            <div className="text-white text-sm font-mono">{frameReport.frame_number}</div>
          </div>
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-[#999] text-xs">Draw Calls</div>
            <div className="text-white text-sm font-mono">{frameReport.frame_draw_calls}</div>
          </div>
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-[#999] text-xs">Batch Count</div>
            <div className="text-white text-sm font-mono">{frameReport.frame_batch_count}</div>
          </div>
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-[#999] text-xs">Commands Processed</div>
            <div className="text-white text-sm font-mono">{frameReport.commands_processed}</div>
          </div>
        </div>
      ) : (
        <div className="text-[#999] text-sm">No frame report data available.</div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#0f0f23]">
      <div className="flex gap-1 border-b border-[#2a2a4a] px-4 pt-2">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => { setActiveTab(t.id); setError(null); }}
            className={`px-4 py-2 text-sm ${activeTab === t.id ? 'bg-[#1a1a2e] text-[#00d4ff] border-t border-x border-[#2a2a4a] rounded-t' : 'text-[#999] hover:text-white'}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-4">
        {loading && <div className="text-[#999] text-sm">Loading...</div>}
        {renderTab()}
      </div>
    </div>
  );
};

export default EngineSpriteBatcherPanel;