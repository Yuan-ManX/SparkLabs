import React, { useState, useEffect, useRef } from 'react';

// Interface for a model entry returned by the LLM Router API
interface RouterModel {
  model_id: string;
  provider_id: string;
  model_types: string[];
  display_name?: string;
}

// Compact model selector for the status bar — fetches models from the LLM Router backend
const ModelSelector: React.FC = () => {
  const [models, setModels] = useState<RouterModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch available models from the LLM Router API on mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await fetch('/api/llm-router/models');
        if (res.ok) {
          const json = await res.json();
          const modelList: RouterModel[] = json?.data?.models || [];
          setModels(modelList);
          if (modelList.length > 0) {
            setSelectedModel(modelList[0].model_id);
          }
        }
      } catch {
        // Backend may be offline — keep empty list
      } finally {
        setLoading(false);
      }
    };
    fetchModels();
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const currentModel = models.find((m) => m.model_id === selectedModel);
  const displayName = currentModel?.display_name || currentModel?.model_id || (loading ? 'Loading...' : 'No Model');

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] text-[#888] hover:text-orange-500 hover:bg-[#1a1a1a] transition-colors"
        title="Select AI Model"
      >
        <i className="fa-solid fa-microchip text-[8px] text-orange-500" />
        <span className="max-w-[120px] truncate">{displayName}</span>
        <i className="fa-solid fa-chevron-down text-[6px] text-[#555]" />
      </button>

      {isOpen && (
        <div className="absolute bottom-full left-0 mb-1 bg-[#0d0d0d] border border-[#222] rounded-lg z-50 min-w-[220px] max-h-[300px] overflow-y-auto shadow-2xl">
          {/* Group models by provider */}
          {Object.entries(
            models.reduce((acc, m) => {
              if (!acc[m.provider_id]) acc[m.provider_id] = [];
              acc[m.provider_id].push(m);
              return acc;
            }, {} as Record<string, RouterModel[]>)
          ).map(([provider, providerModels]) => (
            <div key={provider}>
              <div className="text-[8px] font-bold text-[#444] uppercase tracking-wider px-3 py-1.5 sticky top-0 bg-[#0d0d0d]">
                {provider}
              </div>
              {providerModels.map((model) => (
                <button
                  key={model.model_id}
                  onClick={() => {
                    setSelectedModel(model.model_id);
                    setIsOpen(false);
                  }}
                  className={`w-full text-left px-3 py-1.5 text-[10px] flex items-center gap-2 hover:bg-[#1a1a1a] transition-colors ${
                    model.model_id === selectedModel ? 'text-orange-500' : 'text-[#999]'
                  }`}
                >
                  <i className={`fa-solid ${model.model_id === selectedModel ? 'fa-check' : 'fa-circle'} text-[7px] ${model.model_id === selectedModel ? 'text-orange-500' : 'text-[#333]'}`} />
                  <span className="flex-1 truncate">{model.display_name || model.model_id}</span>
                  <span className="text-[8px] text-[#444]">{model.model_types.join(', ')}</span>
                </button>
              ))}
            </div>
          ))}
          {models.length === 0 && !loading && (
            <div className="px-3 py-4 text-center text-[10px] text-[#444]">
              No models available
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ModelSelector;
