"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT;

interface TilemapStats {
  active_tilemaps: number;
  total_layers: number;
  tileset_count: number;
  collision_tiles: number;
  [key: string]: any;
}

type TabId = 'status' | 'create' | 'edit' | 'layers' | 'query' | 'collision';

const EngineTilemapPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [data, setData] = useState<TilemapStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Status tab
  const [statusTilemapId, setStatusTilemapId] = useState('');

  // Create tilemap fields
  const [tilemapName, setTilemapName] = useState('');
  const [tilemapWidth, setTilemapWidth] = useState('32');
  const [tilemapHeight, setTilemapHeight] = useState('32');
  const [tileWidth, setTileWidth] = useState('16');
  const [tileHeight, setTileHeight] = useState('16');

  // Create tileset fields
  const [tilesetName, setTilesetName] = useState('');
  const [tilesetImage, setTilesetImage] = useState('');
  const [tilesetColumns, setTilesetColumns] = useState('8');
  const [tilesetFirstGid, setTilesetFirstGid] = useState('1');

  // Edit tab
  const [editTilemapId, setEditTilemapId] = useState('');
  const [editLayerId, setEditLayerId] = useState('');
  const [editX, setEditX] = useState('0');
  const [editY, setEditY] = useState('0');
  const [editGid, setEditGid] = useState('1');

  // Fill area
  const [fillStartX, setFillStartX] = useState('0');
  const [fillStartY, setFillStartY] = useState('0');
  const [fillEndX, setFillEndX] = useState('10');
  const [fillEndY, setFillEndY] = useState('10');
  const [fillGid, setFillGid] = useState('1');

  // Layer tab
  const [layerTilemapId, setLayerTilemapId] = useState('');
  const [tileLayerName, setTileLayerName] = useState('');
  const [tileLayerZ, setTileLayerZ] = useState('0');
  const [objectLayerName, setObjectLayerName] = useState('');
  const [objectLayerZ, setObjectLayerZ] = useState('1');
  const [objectName, setObjectName] = useState('');
  const [objectX, setObjectX] = useState('0');
  const [objectY, setObjectY] = useState('0');
  const [objectW, setObjectW] = useState('32');
  const [objectH, setObjectH] = useState('32');

  // Query tab
  const [queryTilemapId, setQueryTilemapId] = useState('');
  const [worldX, setWorldX] = useState('0');
  const [worldY, setWorldY] = useState('0');
  const [tileX, setTileX] = useState('0');
  const [tileY, setTileY] = useState('0');
  const [queryResult, setQueryResult] = useState<string>('');

  // Collision tab
  const [collisionTilemapId, setCollisionTilemapId] = useState('');
  const [collisionData, setCollisionData] = useState<any>(null);

  const tabs = [
    { id: 'status' as TabId, label: 'Status' },
    { id: 'create' as TabId, label: 'Create' },
    { id: 'edit' as TabId, label: 'Edit' },
    { id: 'layers' as TabId, label: 'Layers' },
    { id: 'query' as TabId, label: 'Query' },
    { id: 'collision' as TabId, label: 'Collision' },
  ];

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const endpoint = statusTilemapId
        ? `${API_BASE}/engine/tilemap-system/stats?tilemap_id=${statusTilemapId}`
        : `${API_BASE}/engine/tilemap-system/stats`;
      const res = await fetch(endpoint);
      if (res.ok) setData(await res.json());
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, [statusTilemapId]);

  useEffect(() => {
    fetchData();
    const i = setInterval(fetchData, 15000);
    return () => clearInterval(i);
  }, [fetchData]);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 4000);
  };

  const handleSubmit = async (endpoint: string, body: any) => {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const result = await res.json();
        showMessage('success', 'Operation successful');
        return result;
      } else {
        showMessage('error', `Error: ${res.status}`);
        return null;
      }
    } catch (e: any) {
      showMessage('error', e.message);
      return null;
    }
  };

  const handleGet = async (endpoint: string) => {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`);
      if (res.ok) return await res.json();
      showMessage('error', `Error: ${res.status}`);
      return null;
    } catch (e: any) {
      showMessage('error', e.message);
      return null;
    }
  };

  const renderStatusTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Query Stats</div>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Tilemap ID (optional)</label>
            <input
              type="text"
              value={statusTilemapId}
              onChange={(e) => setStatusTilemapId(e.target.value)}
              placeholder="tilemap_main"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={fetchData}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Refresh Stats
        </button>
      </div>

      {data ? (
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <span className="text-[#999] text-xs">{key.replace(/_/g, ' ')}</span>
              <div className="text-white text-sm font-mono mt-1">
                {typeof value === 'number' ? value.toLocaleString() : String(value)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-[#999] text-sm">No tilemap data available</div>
      )}
    </div>
  );

  const renderCreateTab = () => (
    <div>
      {/* Create Tilemap */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Create Tilemap</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Tilemap Name</label>
            <input type="text" value={tilemapName} onChange={(e) => setTilemapName(e.target.value)} placeholder="main_map" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Map Width (tiles)</label>
            <input type="number" value={tilemapWidth} onChange={(e) => setTilemapWidth(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Map Height (tiles)</label>
            <input type="number" value={tilemapHeight} onChange={(e) => setTilemapHeight(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Tile Width (px)</label>
            <input type="number" value={tileWidth} onChange={(e) => setTileWidth(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Tile Height (px)</label>
            <input type="number" value={tileHeight} onChange={(e) => setTileHeight(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={() => handleSubmit('/engine/tilemap-system/create-tilemap', {
            name: tilemapName, width: parseInt(tilemapWidth, 10), height: parseInt(tilemapHeight, 10),
            tile_width: parseInt(tileWidth, 10), tile_height: parseInt(tileHeight, 10),
          })}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Create Tilemap
        </button>
      </div>

      {/* Create Tileset */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Create Tileset</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Tileset Name</label>
            <input type="text" value={tilesetName} onChange={(e) => setTilesetName(e.target.value)} placeholder="tileset_grassland" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Image Path</label>
            <input type="text" value={tilesetImage} onChange={(e) => setTilesetImage(e.target.value)} placeholder="/assets/tilesets/grassland.png" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Columns</label>
            <input type="number" value={tilesetColumns} onChange={(e) => setTilesetColumns(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">First GID</label>
            <input type="number" value={tilesetFirstGid} onChange={(e) => setTilesetFirstGid(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={() => handleSubmit('/engine/tilemap-system/create-tileset', {
            name: tilesetName, image: tilesetImage, columns: parseInt(tilesetColumns, 10),
            first_gid: parseInt(tilesetFirstGid, 10),
          })}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Create Tileset
        </button>
      </div>
    </div>
  );

  const renderEditTab = () => (
    <div>
      {/* Set Tile */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Set Tile</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Tilemap ID</label>
            <input type="text" value={editTilemapId} onChange={(e) => setEditTilemapId(e.target.value)} placeholder="tilemap_main" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Layer ID</label>
            <input type="text" value={editLayerId} onChange={(e) => setEditLayerId(e.target.value)} placeholder="layer_0" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">X</label>
            <input type="number" value={editX} onChange={(e) => setEditX(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Y</label>
            <input type="number" value={editY} onChange={(e) => setEditY(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Global Tile ID</label>
            <input type="number" value={editGid} onChange={(e) => setEditGid(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={() => handleSubmit('/engine/tilemap-system/set-tile', {
            tilemap_id: editTilemapId, layer_id: editLayerId,
            x: parseInt(editX, 10), y: parseInt(editY, 10),
            global_tile_id: parseInt(editGid, 10),
          })}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          SET Tile
        </button>
      </div>

      {/* Fill Area */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Fill Area</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Start X</label>
            <input type="number" value={fillStartX} onChange={(e) => setFillStartX(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Start Y</label>
            <input type="number" value={fillStartY} onChange={(e) => setFillStartY(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">End X</label>
            <input type="number" value={fillEndX} onChange={(e) => setFillEndX(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">End Y</label>
            <input type="number" value={fillEndY} onChange={(e) => setFillEndY(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Global Tile ID</label>
            <input type="number" value={fillGid} onChange={(e) => setFillGid(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={() => handleSubmit('/engine/tilemap-system/fill-area', {
            tilemap_id: editTilemapId, layer_id: editLayerId,
            start_x: parseInt(fillStartX, 10), start_y: parseInt(fillStartY, 10),
            end_x: parseInt(fillEndX, 10), end_y: parseInt(fillEndY, 10),
            global_tile_id: parseInt(fillGid, 10),
          })}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          FILL Area
        </button>
      </div>
    </div>
  );

  const renderLayersTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div>
          <label className="text-xs text-[#999] mb-1 block">Tilemap ID</label>
          <input type="text" value={layerTilemapId} onChange={(e) => setLayerTilemapId(e.target.value)} placeholder="tilemap_main" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
      </div>

      {/* Add Tile Layer */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Add Tile Layer</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Layer Name</label>
            <input type="text" value={tileLayerName} onChange={(e) => setTileLayerName(e.target.value)} placeholder="ground_layer" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Z-Index</label>
            <input type="number" value={tileLayerZ} onChange={(e) => setTileLayerZ(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={() => handleSubmit('/engine/tilemap-system/add-tile-layer', {
            tilemap_id: layerTilemapId, name: tileLayerName, z_index: parseInt(tileLayerZ, 10),
          })}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Add Tile Layer
        </button>
      </div>

      {/* Add Object Layer */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Add Object Layer</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Layer Name</label>
            <input type="text" value={objectLayerName} onChange={(e) => setObjectLayerName(e.target.value)} placeholder="collision_layer" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Z-Index</label>
            <input type="number" value={objectLayerZ} onChange={(e) => setObjectLayerZ(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={() => handleSubmit('/engine/tilemap-system/add-object-layer', {
            tilemap_id: layerTilemapId, name: objectLayerName, z_index: parseInt(objectLayerZ, 10),
          })}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Add Object Layer
        </button>
      </div>

      {/* Add Object */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Add Object</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Object Name</label>
            <input type="text" value={objectName} onChange={(e) => setObjectName(e.target.value)} placeholder="spawn_point" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div></div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">X</label>
            <input type="number" value={objectX} onChange={(e) => setObjectX(e.target.value)} step="0.1" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Y</label>
            <input type="number" value={objectY} onChange={(e) => setObjectY(e.target.value)} step="0.1" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Width</label>
            <input type="number" value={objectW} onChange={(e) => setObjectW(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Height</label>
            <input type="number" value={objectH} onChange={(e) => setObjectH(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={() => handleSubmit('/engine/tilemap-system/add-object', {
            tilemap_id: layerTilemapId, layer_name: objectLayerName,
            object_name: objectName, x: parseFloat(objectX), y: parseFloat(objectY),
            width: parseFloat(objectW), height: parseFloat(objectH),
          })}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Add Object
        </button>
      </div>
    </div>
  );

  const renderQueryTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Coordinate Converters</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Tilemap ID</label>
          <input type="text" value={queryTilemapId} onChange={(e) => setQueryTilemapId(e.target.value)} placeholder="tilemap_main" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
      </div>

      {/* World to Tile */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">World → Tile</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">World X</label>
            <input type="number" value={worldX} onChange={(e) => setWorldX(e.target.value)} step="0.1" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">World Y</label>
            <input type="number" value={worldY} onChange={(e) => setWorldY(e.target.value)} step="0.1" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            const result = await handleSubmit('/engine/tilemap-system/world-to-tile', {
              tilemap_id: queryTilemapId, world_x: parseFloat(worldX), world_y: parseFloat(worldY),
            });
            if (result) setQueryResult(JSON.stringify(result, null, 2));
          }}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Convert World → Tile
        </button>
      </div>

      {/* Tile to World */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Tile → World</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Tile X</label>
            <input type="number" value={tileX} onChange={(e) => setTileX(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Tile Y</label>
            <input type="number" value={tileY} onChange={(e) => setTileY(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            const result = await handleSubmit('/engine/tilemap-system/tile-to-world', {
              tilemap_id: queryTilemapId, tile_x: parseInt(tileX, 10), tile_y: parseInt(tileY, 10),
            });
            if (result) setQueryResult(JSON.stringify(result, null, 2));
          }}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Convert Tile → World
        </button>
      </div>

      {/* Query Result */}
      {queryResult && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-2">Result</div>
          <textarea
            readOnly
            value={queryResult}
            className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono h-24"
          />
        </div>
      )}
    </div>
  );

  const renderCollisionTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Collision Tiles</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Tilemap ID</label>
          <input type="text" value={collisionTilemapId} onChange={(e) => setCollisionTilemapId(e.target.value)} placeholder="tilemap_main" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button
          onClick={async () => {
            const result = await handleGet(`/engine/tilemap-system/collision-tiles?tilemap_id=${collisionTilemapId}`);
            if (result) setCollisionData(result);
          }}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Get Collision Tiles
        </button>
      </div>

      {collisionData && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-2">Collision Data</div>
          <textarea
            readOnly
            value={JSON.stringify(collisionData, null, 2)}
            className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono h-40"
          />
        </div>
      )}
    </div>
  );

  const renderTab = () => {
    switch (activeTab) {
      case 'status': return renderStatusTab();
      case 'create': return renderCreateTab();
      case 'edit': return renderEditTab();
      case 'layers': return renderLayersTab();
      case 'query': return renderQueryTab();
      case 'collision': return renderCollisionTab();
      default: return null;
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      {message && (
        <div className={`mx-4 mt-2 px-3 py-2 rounded text-sm ${message.type === 'success' ? 'bg-green-900/50 text-green-300 border border-green-700' : 'bg-red-900/50 text-red-300 border border-red-700'}`}>
          {message.text}
        </div>
      )}
      <div className="flex gap-1 border-b border-[#2a2a4a] px-4 pt-2">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2 text-sm ${activeTab === t.id ? 'bg-[#1a1a2e] text-[#00d4ff] border-t border-x border-[#2a2a4a] rounded-t' : 'text-[#999] hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-4">
        {loading && <div className="text-[#999] text-sm mb-2">Loading...</div>}
        {renderTab()}
      </div>
    </div>
  );
};

export default EngineTilemapPanel;