import React, { useState, useCallback, useRef } from 'react';

export interface SceneNode {
  id: string;
  name: string;
  icon: string;
  iconColor: string;
  type: 'entity' | 'component' | 'group';
  visible: boolean;
  locked: boolean;
  children: SceneNode[];
  parentId: string | null;
}

interface SceneOutlinerProps {
  selectedId: string | null;
  onSelect: (id: string, name: string) => void;
  onAddEntity: () => void;
  onDeleteEntity: (id: string) => void;
  onToggleVisibility: (id: string) => void;
  onToggleLock: (id: string) => void;
  onReorder: (dragId: string, dropId: string, position: 'before' | 'after' | 'inside') => void;
  nodes: SceneNode[];
}

const SceneOutliner: React.FC<SceneOutlinerProps> = ({
  selectedId,
  onSelect,
  onAddEntity,
  onDeleteEntity,
  onToggleVisibility,
  onToggleLock,
  onReorder,
  nodes,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set(['root']));
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [dragOverPos, setDragOverPos] = useState<'before' | 'after' | 'inside'>('inside');
  const [contextMenuId, setContextMenuId] = useState<string | null>(null);
  const dragIdRef = useRef<string | null>(null);

  const toggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const filterNodes = useCallback((nodeList: SceneNode[], query: string): SceneNode[] => {
    if (!query) return nodeList;
    return nodeList.filter((n) => {
      if (n.name.toLowerCase().includes(query.toLowerCase())) return true;
      if (n.children.length > 0) return filterNodes(n.children, query).length > 0;
      return false;
    });
  }, []);

  const handleDragStart = useCallback((e: React.DragEvent, id: string) => {
    dragIdRef.current = id;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', id);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, id: string) => {
    e.preventDefault();
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    const y = e.clientY - rect.top;
    const h = rect.height;
    if (y < h * 0.25) {
      setDragOverPos('before');
    } else if (y > h * 0.75) {
      setDragOverPos('after');
    } else {
      setDragOverPos('inside');
    }
    setDragOverId(id);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    const dragId = dragIdRef.current;
    if (dragId && dragId !== targetId) {
      onReorder(dragId, targetId, dragOverPos);
    }
    setDragOverId(null);
    dragIdRef.current = null;
  }, [dragOverPos, onReorder]);

  const handleDragEnd = useCallback(() => {
    setDragOverId(null);
    dragIdRef.current = null;
  }, []);

  const renderNode = (node: SceneNode, depth: number = 0) => {
    const hasChildren = node.children.length > 0;
    const isExpanded = expandedIds.has(node.id);
    const isSelected = selectedId === node.id;
    const isDragOver = dragOverId === node.id;

    let dropClass = '';
    if (isDragOver) {
      if (dragOverPos === 'before') dropClass = 'sl-tree-item-drop-before';
      else if (dragOverPos === 'after') dropClass = 'sl-tree-item-drop-after';
    }

    return (
      <div key={node.id}>
        <div
          className={`sl-tree-item ${isSelected ? 'selected' : ''} ${dropClass}`}
          style={{ paddingLeft: `${8 + depth * 16}px` }}
          onClick={() => onSelect(node.id, node.name)}
          onContextMenu={(e) => { e.preventDefault(); setContextMenuId(node.id); }}
          draggable
          onDragStart={(e) => handleDragStart(e, node.id)}
          onDragOver={(e) => handleDragOver(e, node.id)}
          onDrop={(e) => handleDrop(e, node.id)}
          onDragEnd={handleDragEnd}
        >
          {hasChildren ? (
            <button
              onClick={(e) => { e.stopPropagation(); toggleExpand(node.id); }}
              className="w-4 h-4 flex items-center justify-center text-[9px] text-[#555] hover:text-[#aaa]"
            >
              <i className={`fa-solid fa-chevron-${isExpanded ? 'down' : 'right'}`} />
            </button>
          ) : (
            <span className="w-4" />
          )}
          <i className={`fa-solid ${node.icon} text-[10px]`} style={{ color: node.iconColor }} />
          <span className="flex-1 truncate">{node.name}</span>
          <button
            onClick={(e) => { e.stopPropagation(); onToggleVisibility(node.id); }}
            className="opacity-0 group-hover:opacity-100 text-[9px] text-[#444] hover:text-[#888] w-4 h-4 flex items-center justify-center"
          >
            <i className={`fa-solid ${node.visible ? 'fa-eye' : 'fa-eye-slash'}`} />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onToggleLock(node.id); }}
            className="opacity-0 group-hover:opacity-100 text-[9px] text-[#444] hover:text-[#888] w-4 h-4 flex items-center justify-center"
          >
            <i className={`fa-solid ${node.locked ? 'fa-lock' : 'fa-lock-open'}`} />
          </button>
        </div>
        {hasChildren && isExpanded && (
          <div>
            {filterNodes(node.children, searchQuery).map((child) => renderNode(child, depth + 1))}
          </div>
        )}
        {contextMenuId === node.id && (
          <div
            className="fixed bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg py-1 z-50 min-w-[120px]"
            style={{
              top: '50%',
              left: '50%',
            }}
            onClick={() => setContextMenuId(null)}
          >
            <button
              onClick={() => { onDeleteEntity(node.id); setContextMenuId(null); }}
              className="w-full text-left px-3 py-1.5 text-[11px] text-red-400 hover:bg-[#222]"
            >
              Delete
            </button>
            <button
              onClick={() => { onToggleVisibility(node.id); setContextMenuId(null); }}
              className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222]"
            >
              Toggle Visibility
            </button>
            <button
              onClick={() => { onToggleLock(node.id); setContextMenuId(null); }}
              className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222]"
            >
              Toggle Lock
            </button>
          </div>
        )}
      </div>
    );
  };

  const filteredNodes = filterNodes(nodes, searchQuery);

  return (
    <div className="sl-panel h-full">
      <div className="sl-panel-header">
        <i className="fa-solid fa-sitemap text-[10px] text-orange-500" />
        <span className="sl-panel-header-title">Scene</span>
        <div className="sl-panel-header-actions">
          <button className="sl-panel-header-btn" onClick={onAddEntity} title="Add Entity">
            <i className="fa-solid fa-plus" />
          </button>
        </div>
      </div>
      <div className="px-2 py-1 border-b border-[#1e1e1e]">
        <input
          type="text"
          placeholder="Search scene..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="sl-property-input w-full"
        />
      </div>
      <div className="flex-1 overflow-y-auto py-1">
        {filteredNodes.map((node) => renderNode(node))}
      </div>
    </div>
  );
};

export default SceneOutliner;
