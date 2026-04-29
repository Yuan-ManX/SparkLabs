import React, { useState, useCallback } from 'react';

interface SettingItem {
  key: string;
  label: string;
  type: 'toggle' | 'select' | 'slider' | 'text' | 'number';
  value: unknown;
  options?: { label: string; value: string }[];
  min?: number;
  max?: number;
  step?: number;
  description?: string;
}

interface SettingSection {
  id: string;
  label: string;
  icon: string;
  color: string;
  items: SettingItem[];
}

const SECTIONS: SettingSection[] = [
  {
    id: 'general', label: 'General', icon: 'fa-gear', color: '#888',
    items: [
      { key: 'auto_save', label: 'Auto Save', type: 'toggle', value: true, description: 'Automatically save changes every 30 seconds' },
      { key: 'auto_save_interval', label: 'Auto Save Interval (s)', type: 'number', value: 30, min: 5, max: 300 },
      { key: 'theme', label: 'Theme', type: 'select', value: 'dark', options: [{ label: 'Dark', value: 'dark' }, { label: 'Darker', value: 'darker' }, { label: 'Midnight', value: 'midnight' }] },
      { key: 'language', label: 'Language', type: 'select', value: 'en', options: [{ label: 'English', value: 'en' }, { label: 'Chinese', value: 'zh' }, { label: 'Japanese', value: 'ja' }] },
      { key: 'show_splash', label: 'Show Splash Screen', type: 'toggle', value: true },
    ],
  },
  {
    id: 'editor', label: 'Editor', icon: 'fa-code', color: '#06b6d4',
    items: [
      { key: 'font_size', label: 'Font Size', type: 'number', value: 12, min: 8, max: 24 },
      { key: 'tab_size', label: 'Tab Size', type: 'select', value: '2', options: [{ label: '2 spaces', value: '2' }, { label: '4 spaces', value: '4' }] },
      { key: 'word_wrap', label: 'Word Wrap', type: 'toggle', value: true },
      { key: 'minimap', label: 'Show Minimap', type: 'toggle', value: false },
      { key: 'line_numbers', label: 'Line Numbers', type: 'toggle', value: true },
      { key: 'bracket_matching', label: 'Bracket Matching', type: 'toggle', value: true },
    ],
  },
  {
    id: 'viewport', label: 'Viewport', icon: 'fa-gamepad', color: '#22c55e',
    items: [
      { key: 'fps_limit', label: 'FPS Limit', type: 'select', value: '60', options: [{ label: '30 FPS', value: '30' }, { label: '60 FPS', value: '60' }, { label: '120 FPS', value: '120' }, { label: 'Unlimited', value: '0' }] },
      { key: 'grid_opacity', label: 'Grid Opacity', type: 'slider', value: 30, min: 0, max: 100 },
      { key: 'antialiasing', label: 'Anti-Aliasing', type: 'toggle', value: true },
      { key: 'shadows', label: 'Shadows', type: 'toggle', value: true },
      { key: 'vignette', label: 'Vignette Effect', type: 'toggle', value: false },
    ],
  },
  {
    id: 'ai', label: 'AI Engine', icon: 'fa-brain', color: '#f97316',
    items: [
      { key: 'ai_model', label: 'Default AI Model', type: 'select', value: 'sparkai', options: [{ label: 'SparkAI', value: 'sparkai' }, { label: 'GPT-4', value: 'gpt-4' }, { label: 'Claude 3', value: 'claude-3' }] },
      { key: 'creativity', label: 'Creativity', type: 'slider', value: 70, min: 0, max: 100, description: 'Higher values produce more creative but less predictable results' },
      { key: 'coherence', label: 'Coherence', type: 'slider', value: 80, min: 0, max: 100 },
      { key: 'auto_validate', label: 'Auto-Validate Generated Code', type: 'toggle', value: true },
      { key: 'show_thinking', label: 'Show AI Thinking Process', type: 'toggle', value: false },
      { key: 'parallel_agents', label: 'Max Parallel Agents', type: 'number', value: 4, min: 1, max: 16 },
    ],
  },
  {
    id: 'performance', label: 'Performance', icon: 'fa-gauge-high', color: '#ef4444',
    items: [
      { key: 'gpu_acceleration', label: 'GPU Acceleration', type: 'toggle', value: true },
      { key: 'cache_size', label: 'Cache Size (MB)', type: 'number', value: 512, min: 64, max: 4096 },
      { key: 'worker_threads', label: 'Worker Threads', type: 'number', value: 4, min: 1, max: 16 },
      { key: 'lazy_loading', label: 'Lazy Loading', type: 'toggle', value: true },
    ],
  },
  {
    id: 'export', label: 'Export', icon: 'fa-file-export', color: '#8b5cf6',
    items: [
      { key: 'default_format', label: 'Default Format', type: 'select', value: 'html5', options: [{ label: 'HTML5', value: 'html5' }, { label: 'WebGL', value: 'webgl' }, { label: 'Desktop', value: 'desktop' }, { label: 'Mobile', value: 'mobile' }] },
      { key: 'minify', label: 'Minify Output', type: 'toggle', value: true },
      { key: 'include_source', label: 'Include Source Maps', type: 'toggle', value: false },
      { key: 'compress_assets', label: 'Compress Assets', type: 'toggle', value: true },
    ],
  },
];

const SettingsPanel: React.FC = () => {
  const [settings, setSettings] = useState<Record<string, Record<string, unknown>>>(() => {
    const initial: Record<string, Record<string, unknown>> = {};
    SECTIONS.forEach((section) => {
      initial[section.id] = {};
      section.items.forEach((item) => {
        initial[section.id][item.key] = item.value;
      });
    });
    return initial;
  });

  const [activeSection, setActiveSection] = useState('general');
  const [searchQuery, setSearchQuery] = useState('');

  const handleSettingChange = useCallback((sectionId: string, key: string, value: unknown) => {
    setSettings((prev) => ({
      ...prev,
      [sectionId]: { ...prev[sectionId], [key]: value },
    }));
  }, []);

  const currentSection = SECTIONS.find((s) => s.id === activeSection);

  const filteredItems = currentSection?.items.filter(
    (item) => !searchQuery || item.label.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  return (
    <div className="sl-panel h-full">
      <div className="sl-panel-header">
        <i className="fa-solid fa-gear text-[10px] text-orange-500" />
        <span className="sl-panel-header-title">Settings</span>
      </div>
      <div className="flex-1 flex overflow-hidden">
        <div className="w-48 border-r border-[#1e1e1e] bg-[#0d0d0d] overflow-y-auto flex-shrink-0">
          <div className="p-2">
            <input
              type="text"
              placeholder="Search settings..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="sl-property-input w-full mb-2"
            />
          </div>
          {SECTIONS.map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`w-full text-left px-3 py-2 text-[11px] flex items-center gap-2 transition-colors ${
                activeSection === section.id
                  ? 'bg-orange-500/10 text-orange-500 border-l-2 border-orange-500'
                  : 'text-[#777] hover:bg-[#1a1a1a] hover:text-[#aaa] border-l-2 border-transparent'
              }`}
            >
              <i className={`fa-solid ${section.icon} text-[9px]`} style={{ color: section.color }} />
              {section.label}
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {currentSection && (
            <>
              <div className="flex items-center gap-2 mb-4">
                <i className={`fa-solid ${currentSection.icon} text-sm`} style={{ color: currentSection.color }} />
                <h2 className="text-sm font-semibold text-[#ccc]">{currentSection.label}</h2>
              </div>
              <div className="space-y-4">
                {filteredItems.map((item) => (
                  <div key={item.key} className="flex items-start gap-4">
                    <div className="flex-1">
                      <div className="text-[12px] text-[#bbb]">{item.label}</div>
                      {item.description && (
                        <div className="text-[10px] text-[#555] mt-0.5">{item.description}</div>
                      )}
                    </div>
                    <div className="w-48 flex-shrink-0">
                      {item.type === 'toggle' && (
                        <button
                          onClick={() => handleSettingChange(currentSection.id, item.key, !settings[currentSection.id]?.[item.key])}
                          className={`w-10 h-5 rounded-full transition-colors relative ${
                            settings[currentSection.id]?.[item.key] ? 'bg-orange-500' : 'bg-[#333]'
                          }`}
                        >
                          <div className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform ${
                            settings[currentSection.id]?.[item.key] ? 'translate-x-5' : 'translate-x-0.5'
                          }`} />
                        </button>
                      )}
                      {item.type === 'select' && (
                        <select
                          value={settings[currentSection.id]?.[item.key] as string || ''}
                          onChange={(e) => handleSettingChange(currentSection.id, item.key, e.target.value)}
                          className="sl-property-input w-full"
                        >
                          {item.options?.map((opt) => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                        </select>
                      )}
                      {item.type === 'slider' && (
                        <div className="flex items-center gap-2">
                          <input
                            type="range"
                            value={settings[currentSection.id]?.[item.key] as number || 0}
                            min={item.min || 0}
                            max={item.max || 100}
                            step={item.step || 1}
                            onChange={(e) => handleSettingChange(currentSection.id, item.key, parseInt(e.target.value))}
                            className="flex-1 accent-orange-500"
                          />
                          <span className="text-[10px] text-[#666] w-8 text-right">{settings[currentSection.id]?.[item.key] as number}</span>
                        </div>
                      )}
                      {item.type === 'number' && (
                        <input
                          type="number"
                          value={settings[currentSection.id]?.[item.key] as number || 0}
                          min={item.min}
                          max={item.max}
                          onChange={(e) => handleSettingChange(currentSection.id, item.key, parseInt(e.target.value) || 0)}
                          className="sl-property-input w-full"
                        />
                      )}
                      {item.type === 'text' && (
                        <input
                          type="text"
                          value={settings[currentSection.id]?.[item.key] as string || ''}
                          onChange={(e) => handleSettingChange(currentSection.id, item.key, e.target.value)}
                          className="sl-property-input w-full"
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
